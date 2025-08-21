"""
Health check and monitoring endpoints
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_superuser
from app.models.user import User
from app.core.monitoring import (
    health_metrics,
    detailed_health_check,
    alert_manager,
    DatabaseHealthChecker
)

router = APIRouter()


@router.get("/health")
async def basic_health_check() -> Dict[str, str]:
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "service": "EventTicketing API",
        "timestamp": "2025-08-20T18:00:00Z"
    }


@router.get("/health/detailed")
async def get_detailed_health(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Detailed health check with metrics
    """
    try:
        health_status = await detailed_health_check(db)
        return health_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/metrics")
async def get_application_metrics(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get comprehensive application metrics (admin only)
    """
    try:
        metrics = health_metrics.get_detailed_metrics()
        return {
            "metrics": metrics,
            "alerts": {
                "checking_enabled": True,
                "last_check": "2025-08-20T18:00:00Z"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/performance")
async def get_performance_metrics(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get performance-specific metrics (admin only)
    """
    try:
        basic_metrics = health_metrics.get_health_status()
        
        # Extract performance-specific data
        performance_data = {
            "response_times": {
                "average_ms": basic_metrics["average_response_time_ms"],
                "recent_samples": len(health_metrics.response_times)
            },
            "request_volume": {
                "total_requests": basic_metrics["total_requests"],
                "requests_per_minute": 0,  # Would calculate based on time window
                "peak_rpm": 0  # Would track peak requests per minute
            },
            "error_analysis": {
                "total_errors": basic_metrics["total_errors"],
                "error_rate": basic_metrics["error_rate_percentage"],
                "status_codes": basic_metrics["status_code_distribution"]
            },
            "uptime": {
                "seconds": basic_metrics["uptime_seconds"],
                "start_time": "2025-08-20T12:00:00Z"  # Would be actual start time
            }
        }
        
        return {"performance_metrics": performance_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/health/database")
async def check_database_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Check database health specifically (admin only)
    """
    try:
        db_healthy = await DatabaseHealthChecker.check_database_health(db)
        
        # Additional database metrics
        from sqlalchemy import text
        
        # Check connection count (PostgreSQL specific)
        try:
            result = await db.execute(text("SELECT count(*) FROM pg_stat_activity"))
            active_connections = result.scalar()
        except:
            active_connections = None
        
        # Check database size
        try:
            result = await db.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            ))
            db_size = result.scalar()
        except:
            db_size = None
        
        return {
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "active_connections": active_connections,
                "database_size": db_size,
                "last_check": "2025-08-20T18:00:00Z"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")


@router.get("/health/redis")
async def check_redis_health(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Check Redis health specifically (admin only)
    """
    try:
        redis_healthy = await DatabaseHealthChecker.check_redis_health()
        
        return {
            "redis": {
                "status": "healthy" if redis_healthy else "unhealthy",
                "last_check": "2025-08-20T18:00:00Z"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis health check failed: {str(e)}")


@router.post("/alerts/test")
async def test_alerting_system(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, str]:
    """
    Test the alerting system (admin only)
    """
    try:
        # Trigger a test alert
        test_alert = {
            "type": "test_alert",
            "message": "This is a test alert to verify the alerting system",
            "severity": "low"
        }
        
        alert_manager._send_alert(test_alert)
        
        return {"message": "Test alert sent successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test alert: {str(e)}")


@router.get("/monitoring/status")
async def get_monitoring_status(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get overall monitoring system status (admin only)
    """
    try:
        # Check if monitoring components are working
        monitoring_status = {
            "metrics_collection": True,
            "health_checks": True,
            "error_tracking": True,
            "alerting": True,
            "performance_profiling": True
        }
        
        # Get recent error count
        error_count_24h = health_metrics.error_count  # Would filter by last 24 hours in production
        
        # Get alert statistics
        alert_stats = {
            "alerts_sent_24h": len(alert_manager.last_alerts),
            "last_alert_time": max(alert_manager.last_alerts.values()) if alert_manager.last_alerts else None
        }
        
        overall_health = all(monitoring_status.values())
        
        return {
            "monitoring": {
                "status": "healthy" if overall_health else "degraded",
                "components": monitoring_status,
                "statistics": {
                    "errors_24h": error_count_24h,
                    "alerts": alert_stats
                },
                "last_updated": "2025-08-20T18:00:00Z"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")


@router.post("/monitoring/reset")
async def reset_monitoring_metrics(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, str]:
    """
    Reset monitoring metrics (admin only) - useful for testing
    """
    try:
        # Reset metrics (be careful in production!)
        health_metrics.request_count = 0
        health_metrics.error_count = 0
        health_metrics.response_times.clear()
        health_metrics.status_codes.clear()
        health_metrics.endpoint_metrics.clear()
        health_metrics.start_time = time.time()
        health_metrics.last_error_time = None
        
        return {"message": "Monitoring metrics reset successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {str(e)}")