"""
Security middleware for FastAPI application
"""
import hashlib
import hmac
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis

from app.core.config import settings

# Rate limiting storage
class RateLimitStorage:
    """Rate limiting storage using Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.fallback_storage: Dict[str, Any] = defaultdict(list)
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                await self.redis_client.ping()
        except Exception:
            # Fall back to in-memory storage for development
            self.redis_client = None
    
    async def get_requests(self, key: str, window: int) -> int:
        """Get number of requests in the time window"""
        current_time = time.time()
        window_start = current_time - window
        
        if self.redis_client:
            try:
                # Use Redis sorted set for efficient time-based queries
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
                pipe.zcard(key)  # Count current entries
                pipe.expire(key, window)  # Set expiration
                results = await pipe.execute()
                return results[1] if results[1] else 0
            except Exception:
                # Fall back to in-memory
                pass
        
        # In-memory fallback
        requests = self.fallback_storage[key]
        # Remove old requests
        self.fallback_storage[key] = [req_time for req_time in requests if req_time > window_start]
        return len(self.fallback_storage[key])
    
    async def add_request(self, key: str, window: int):
        """Add a request to the storage"""
        current_time = time.time()
        
        if self.redis_client:
            try:
                await self.redis_client.zadd(key, {str(current_time): current_time})
                await self.redis_client.expire(key, window)
                return
            except Exception:
                pass
        
        # In-memory fallback
        self.fallback_storage[key].append(current_time)

# Global rate limit storage
rate_limit_storage = RateLimitStorage()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers (load balancer, proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key"""
        client_ip = self.get_client_ip(request)
        
        # Different limits for different endpoints
        if request.url.path.startswith("/api/v1/auth"):
            return f"auth:{client_ip}"
        elif request.url.path.startswith("/api/v1/files"):
            return f"files:{client_ip}"
        else:
            return f"api:{client_ip}"
    
    def get_rate_limits(self, key: str) -> tuple[int, int]:
        """Get rate limits based on key type"""
        if key.startswith("auth:"):
            return 10, 60  # 10 requests per minute for auth
        elif key.startswith("files:"):
            return 20, 60  # 20 requests per minute for file uploads
        else:
            return self.calls, self.period  # Default limits
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health", "/api/v1/health"]:
            return await call_next(request)
        
        key = self.get_rate_limit_key(request)
        calls, period = self.get_rate_limits(key)
        
        # Check current request count
        current_requests = await rate_limit_storage.get_requests(key, period)
        
        if current_requests >= calls:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": period,
                    "limit": calls,
                    "window": period
                },
                headers={
                    "Retry-After": str(period),
                    "X-RateLimit-Limit": str(calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + period)
                }
            )
        
        # Add the request to storage
        await rate_limit_storage.add_request(key, period)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        remaining = max(0, calls - current_requests - 1)
        response.headers["X-RateLimit-Limit"] = str(calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + period)
        
        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key.encode()
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).hexdigest()
        return f"{timestamp}.{signature}"
    
    def validate_csrf_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        try:
            timestamp, signature = token.split(".", 1)
            
            # Check if token is not too old (1 hour)
            if int(time.time()) - int(timestamp) > 3600:
                return False
            
            message = f"{session_id}:{timestamp}"
            expected_signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, TypeError):
            return False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF protection for GET, HEAD, OPTIONS
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
            # Add CSRF token to response for forms
            if "text/html" in response.headers.get("content-type", ""):
                # In a real implementation, you'd add the CSRF token to the HTML
                pass
            return response
        
        # Skip for API endpoints with proper authentication
        if request.url.path.startswith("/api/"):
            # API endpoints should use proper authentication instead of CSRF
            return await call_next(request)
        
        # Check CSRF token for state-changing requests
        csrf_token = request.headers.get("X-CSRF-Token") or request.cookies.get("csrf_token")
        session_id = request.cookies.get("session_id", "")
        
        if not csrf_token or not self.validate_csrf_token(csrf_token, session_id):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token validation failed"}
            )
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware for security monitoring"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request details
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log security-relevant information
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "user_agent": user_agent,
        }
        
        # Log suspicious activities
        if response.status_code == 401:
            log_data["event"] = "unauthorized_access"
        elif response.status_code == 403:
            log_data["event"] = "forbidden_access"
        elif response.status_code == 429:
            log_data["event"] = "rate_limit_exceeded"
        elif response.status_code >= 500:
            log_data["event"] = "server_error"
        
        # In production, you'd send this to a logging service
        if "event" in log_data:
            print(f"SECURITY_LOG: {log_data}")
        
        # Add request ID for tracing
        response.headers["X-Request-ID"] = str(int(time.time() * 1000000))
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


# Initialize rate limiting storage on startup
async def init_security_middleware():
    """Initialize security middleware components"""
    await rate_limit_storage.initialize()