from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.security_middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware, 
    RequestLoggingMiddleware,
    init_security_middleware
)
from app.core.monitoring import (
    MonitoringMiddleware,
    setup_monitoring,
    http_exception_handler_with_logging,
    general_exception_handler
)
from app.core.caching import cache_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_security_middleware()
    setup_monitoring()
    
    # Initialize cache manager
    await cache_manager.initialize()
    
    # Start WebSocket heartbeat task
    import asyncio
    from app.api.v1.endpoints.websocket import heartbeat_task
    asyncio.create_task(heartbeat_task())
    
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="EventTicketing API - Secure event management and ticketing platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Monitoring and security middleware (order matters)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# Trusted host middleware (prevent host header injection)
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )

# CORS middleware - allow all origins for development
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip('/') for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )


@app.get("/")
async def root():
    return {"message": "Welcome to EventTicketing API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    cache_stats = await cache_manager.get_stats()
    return {
        "status": "healthy", 
        "service": "EventTicketing API",
        "cache": {
            "status": "connected" if cache_stats["redis_connected"] else "disconnected",
            "hit_rate": f"{cache_stats['hit_rate']:.1f}%"
        }
    }


# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler_with_logging)
app.add_exception_handler(StarletteHTTPException, http_exception_handler_with_logging)
app.add_exception_handler(Exception, general_exception_handler)

# Import and include API routers
from app.api.v1.api import api_router

app.include_router(api_router, prefix=settings.API_V1_STR) 