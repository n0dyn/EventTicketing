"""
Comprehensive monitoring and error handling infrastructure
"""
import logging
import traceback
import time
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/app.log', mode='a') if settings.ENVIRONMENT == "production" else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


class HealthMetrics:
    """Application health and performance metrics"""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.response_times: deque = deque(maxlen=1000)  # Store last 1000 response times
        self.status_codes: Dict[int, int] = defaultdict(int)
        self.endpoint_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "avg_response_time": 0,
            "total_time": 0
        })
        self.start_time = time.time()
        self.last_error_time = None
        self.database_health = True
        self.redis_health = True
        
    def add_request_metric(self, endpoint: str, method: str, status_code: int, response_time: float):
        """Add request metric"""
        self.request_count += 1
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1
        
        # Endpoint-specific metrics
        key = f"{method} {endpoint}"
        metrics = self.endpoint_metrics[key]
        metrics["count"] += 1
        metrics["total_time"] += response_time
        metrics["avg_response_time"] = metrics["total_time"] / metrics["count"]
        
        if status_code >= 400:
            self.error_count += 1
            metrics["errors"] += 1
            self.last_error_time = datetime.utcnow()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        # Calculate error rate
        error_rate = (self.error_count / self.request_count * 100) if self.request_count > 0 else 0
        
        # Health status determination
        is_healthy = (
            error_rate < 5 and  # Less than 5% error rate
            avg_response_time < 1000 and  # Less than 1 second average response time
            self.database_health and
            self.redis_health
        )
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percentage": round(error_rate, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "database_healthy": self.database_health,
            "redis_healthy": self.redis_health,
            "status_code_distribution": dict(self.status_codes),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        health_status = self.get_health_status()
        
        # Top endpoints by request count
        top_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:10]
        
        # Slowest endpoints
        slowest_endpoints = sorted(
            [(k, v) for k, v in self.endpoint_metrics.items() if v["count"] > 0],
            key=lambda x: x[1]["avg_response_time"],
            reverse=True
        )[:10]
        
        return {
            **health_status,
            "detailed_metrics": {
                "top_endpoints": [
                    {
                        "endpoint": endpoint,
                        "requests": metrics["count"],
                        "errors": metrics["errors"],
                        "avg_response_time": round(metrics["avg_response_time"], 2),
                        "error_rate": round((metrics["errors"] / metrics["count"] * 100), 2)
                    }
                    for endpoint, metrics in top_endpoints
                ],
                "slowest_endpoints": [
                    {
                        "endpoint": endpoint,
                        "avg_response_time": round(metrics["avg_response_time"], 2),
                        "requests": metrics["count"]
                    }
                    for endpoint, metrics in slowest_endpoints
                ]
            }
        }


# Global metrics instance
health_metrics = HealthMetrics()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Add metrics
            health_metrics.add_request_metric(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=process_time
            )
            
            # Add response time header
            response.headers["X-Process-Time"] = str(round(process_time, 2))
            
            # Log slow requests
            if process_time > 1000:  # Log requests taking more than 1 second
                logger.warning(
                    f"Slow request: {request.method} {request.url.path} "
                    f"took {process_time:.2f}ms"
                )
            
            return response
            
        except Exception as e:
            # Calculate response time for errors too
            process_time = (time.time() - start_time) * 1000
            
            # Add error metrics
            health_metrics.add_request_metric(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                response_time=process_time
            )
            
            # Log the error
            logger.error(
                f"Request error: {request.method} {request.url.path} "
                f"- {str(e)}\n{traceback.format_exc()}"
            )
            
            # Re-raise the exception
            raise


class DatabaseHealthChecker:
    """Database health monitoring"""
    
    @staticmethod
    async def check_database_health(db: AsyncSession) -> bool:
        """Check database connectivity and health"""
        try:
            # Simple query to test connection
            result = await db.execute("SELECT 1")
            health_metrics.database_health = True
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            health_metrics.database_health = False
            return False
    
    @staticmethod
    async def check_redis_health() -> bool:
        """Check Redis connectivity and health"""
        try:
            # This would check Redis in a real implementation
            # For now, we'll assume it's healthy
            health_metrics.redis_health = True
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            health_metrics.redis_health = False
            return False


class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def log_error(
        error: Exception,
        request: Request,
        user_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Log error with context"""
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "url": str(request.url),
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else "unknown",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "additional_context": additional_context or {}
        }
        
        # Log the full traceback for debugging
        logger.error(
            f"Application Error: {error_context}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        # In production, you'd send this to an error tracking service like Sentry
        
    @staticmethod
    def create_error_response(
        error: Exception,
        status_code: int = 500,
        user_message: str = "An internal error occurred"
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        error_id = f"err_{int(time.time() * 1000000)}"  # Simple error ID
        
        response = {
            "error": {
                "id": error_id,
                "message": user_message,
                "timestamp": datetime.utcnow().isoformat(),
                "status_code": status_code
            }
        }
        
        # Include error details in development
        if settings.ENVIRONMENT == "development":
            response["error"]["details"] = str(error)
            response["error"]["type"] = type(error).__name__
        
        return response


class AlertManager:
    """Alert management for critical issues"""
    
    def __init__(self):
        self.alert_thresholds = {
            "error_rate": 10.0,  # 10% error rate
            "response_time": 2000,  # 2 seconds
            "database_down": True,
            "high_memory": 85.0,  # 85% memory usage
        }
        self.last_alerts = {}
        self.alert_cooldown = 300  # 5 minutes between similar alerts
    
    def check_alerts(self):
        """Check if any alerts should be triggered"""
        current_time = time.time()
        metrics = health_metrics.get_health_status()
        
        alerts_to_send = []
        
        # Check error rate
        if metrics["error_rate_percentage"] > self.alert_thresholds["error_rate"]:
            alert_key = "high_error_rate"
            if self._should_send_alert(alert_key, current_time):
                alerts_to_send.append({
                    "type": "high_error_rate",
                    "message": f"Error rate is {metrics['error_rate_percentage']:.2f}%",
                    "severity": "high"
                })
        
        # Check response time
        if metrics["average_response_time_ms"] > self.alert_thresholds["response_time"]:
            alert_key = "slow_response"
            if self._should_send_alert(alert_key, current_time):
                alerts_to_send.append({
                    "type": "slow_response",
                    "message": f"Average response time is {metrics['average_response_time_ms']:.2f}ms",
                    "severity": "medium"
                })
        
        # Check database health
        if not metrics["database_healthy"]:
            alert_key = "database_down"
            if self._should_send_alert(alert_key, current_time):
                alerts_to_send.append({
                    "type": "database_down",
                    "message": "Database health check failed",
                    "severity": "critical"
                })
        
        # Send alerts
        for alert in alerts_to_send:
            self._send_alert(alert)
    
    def _should_send_alert(self, alert_key: str, current_time: float) -> bool:
        """Check if enough time has passed since last alert"""
        last_sent = self.last_alerts.get(alert_key, 0)
        return current_time - last_sent > self.alert_cooldown
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert (placeholder - would integrate with actual alerting system)"""
        logger.critical(f"ALERT: {alert['type']} - {alert['message']} (Severity: {alert['severity']})")
        self.last_alerts[alert["type"]] = time.time()
        
        # In production, this would:
        # - Send emails to administrators
        # - Post to Slack/Discord
        # - Create PagerDuty incidents
        # - Send SMS for critical alerts


# Global alert manager
alert_manager = AlertManager()


class PerformanceProfiler:
    """Performance profiling utilities"""
    
    @staticmethod
    @asynccontextmanager
    async def profile_operation(operation_name: str):
        """Context manager for profiling operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000
            logger.info(f"Operation '{operation_name}' took {duration:.2f}ms")
            
            # Log slow operations
            if duration > 500:  # Log operations taking more than 500ms
                logger.warning(f"Slow operation: '{operation_name}' took {duration:.2f}ms")
    
    @staticmethod
    def profile_query(query_name: str):
        """Decorator for profiling database queries"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                async with PerformanceProfiler.profile_operation(f"DB Query: {query_name}"):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


# Exception handlers
async def http_exception_handler_with_logging(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with logging"""
    ErrorHandler.log_error(
        error=exc,
        request=request,
        additional_context={"status_code": exc.status_code}
    )
    
    # Call the default handler
    return await http_exception_handler(request, exc)


async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unhandled exceptions"""
    ErrorHandler.log_error(error=exc, request=request)
    
    error_response = ErrorHandler.create_error_response(
        error=exc,
        status_code=500,
        user_message="An internal server error occurred"
    )
    
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content=error_response
    )


# Health check functions
async def detailed_health_check(db: AsyncSession) -> Dict[str, Any]:
    """Comprehensive health check"""
    # Check database
    db_healthy = await DatabaseHealthChecker.check_database_health(db)
    
    # Check Redis
    redis_healthy = await DatabaseHealthChecker.check_redis_health()
    
    # Get application metrics
    app_metrics = health_metrics.get_health_status()
    
    # System metrics (simplified - in production you'd use psutil)
    import os
    try:
        load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
    except:
        load_avg = 0
    
    overall_health = (
        db_healthy and 
        redis_healthy and 
        app_metrics["status"] == "healthy" and
        load_avg < 2.0
    )
    
    return {
        "status": "healthy" if overall_health else "unhealthy",
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "application": app_metrics["status"]
        },
        "metrics": app_metrics,
        "system": {
            "load_average": round(load_avg, 2)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# Initialize monitoring
def setup_monitoring():
    """Setup monitoring components"""
    logger.info("Initializing monitoring system...")
    
    # Start alert checking (in production, you'd use a background task)
    # For now, we'll check alerts on demand
    
    logger.info("Monitoring system initialized successfully")


# Performance decorator
def monitor_performance(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            async with PerformanceProfiler.profile_operation(operation_name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                logger.info(f"Operation '{operation_name}' took {duration:.2f}ms")
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                logger.error(f"Operation '{operation_name}' failed after {duration:.2f}ms: {str(e)}")
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator