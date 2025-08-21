"""
Analytics and reporting endpoints
"""
from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_current_active_superuser
from app.models.user import User
from app.services.analytics_service import (
    revenue_analytics,
    event_analytics,
    user_analytics,
    organization_analytics,
    DateRange
)

router = APIRouter()


@router.get("/revenue/overview")
async def get_revenue_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for analytics"),
    start_date: Optional[date] = Query(None, description="Custom start date (for CUSTOM range)"),
    end_date: Optional[date] = Query(None, description="Custom end date (for CUSTOM range)"),
    organization_id: Optional[int] = Query(None, description="Filter by organization")
) -> Dict[str, Any]:
    """
    Get comprehensive revenue overview (admin only)
    """
    try:
        overview = await revenue_analytics.get_revenue_overview(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            organization_id=organization_id
        )
        
        return overview
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get revenue overview: {str(e)}")


@router.get("/revenue/trend")
async def get_revenue_trend(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for trend"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date"),
    organization_id: Optional[int] = Query(None, description="Filter by organization")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get daily revenue trend data (admin only)
    """
    try:
        trend_data = await revenue_analytics.get_daily_revenue_trend(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            organization_id=organization_id
        )
        
        return {"trend_data": trend_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get revenue trend: {str(e)}")


@router.get("/events/{event_id}/performance")
async def get_event_performance(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get comprehensive event performance metrics
    """
    try:
        # TODO: Add authorization check - user should own the event or be admin
        
        performance = await event_analytics.get_event_performance(
            db=db,
            event_id=event_id
        )
        
        if "error" in performance:
            raise HTTPException(status_code=404, detail=performance["error"])
        
        return performance
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get event performance: {str(e)}")


@router.get("/events/top")
async def get_top_events(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for analysis"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date"),
    limit: int = Query(10, ge=1, le=50, description="Number of top events to return"),
    sort_by: str = Query("revenue", regex="^(revenue|orders)$", description="Sort by revenue or orders")
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get top performing events (admin only)
    """
    try:
        top_events = await event_analytics.get_top_events(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            sort_by=sort_by
        )
        
        return {"top_events": top_events}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top events: {str(e)}")


@router.get("/users/growth")
async def get_user_growth_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for analysis"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date")
) -> Dict[str, Any]:
    """
    Get user growth and engagement metrics (admin only)
    """
    try:
        growth_metrics = await user_analytics.get_user_growth_metrics(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date
        )
        
        return growth_metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user growth metrics: {str(e)}")


@router.get("/organizations/{organization_id}/performance")
async def get_organization_performance(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for analysis"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date")
) -> Dict[str, Any]:
    """
    Get organization performance metrics
    """
    try:
        # TODO: Add authorization check - user should own the organization or be admin
        
        performance = await organization_analytics.get_organization_performance(
            db=db,
            organization_id=organization_id,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date
        )
        
        if "error" in performance:
            raise HTTPException(status_code=404, detail=performance["error"])
        
        return performance
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organization performance: {str(e)}")


@router.get("/dashboard")
async def get_analytics_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for dashboard"),
    organization_id: Optional[int] = Query(None, description="Filter by organization")
) -> Dict[str, Any]:
    """
    Get comprehensive analytics dashboard data (admin only)
    """
    try:
        # Get multiple analytics in parallel
        import asyncio
        
        # Revenue overview
        revenue_overview_task = revenue_analytics.get_revenue_overview(
            db=db,
            date_range=date_range,
            organization_id=organization_id
        )
        
        # Top events
        top_events_task = event_analytics.get_top_events(
            db=db,
            date_range=date_range,
            limit=5
        )
        
        # User growth
        user_growth_task = user_analytics.get_user_growth_metrics(
            db=db,
            date_range=date_range
        )
        
        # Revenue trend
        revenue_trend_task = revenue_analytics.get_daily_revenue_trend(
            db=db,
            date_range=date_range,
            organization_id=organization_id
        )
        
        # Execute all tasks concurrently
        revenue_overview, top_events, user_growth, revenue_trend = await asyncio.gather(
            revenue_overview_task,
            top_events_task,
            user_growth_task,
            revenue_trend_task
        )
        
        return {
            "dashboard": {
                "revenue_overview": revenue_overview,
                "top_events": top_events,
                "user_growth": user_growth,
                "revenue_trend": revenue_trend
            },
            "filters": {
                "date_range": date_range,
                "organization_id": organization_id
            },
            "generated_at": "2025-08-20T18:00:00Z"  # In production, use datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/export/revenue")
async def export_revenue_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    date_range: DateRange = Query(DateRange.LAST_30_DAYS, description="Date range for export"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date"),
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    format: str = Query("json", regex="^(json|csv)$", description="Export format")
) -> Any:
    """
    Export revenue report in specified format (admin only)
    """
    try:
        # Get revenue data
        overview = await revenue_analytics.get_revenue_overview(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            organization_id=organization_id
        )
        
        trend_data = await revenue_analytics.get_daily_revenue_trend(
            db=db,
            date_range=date_range,
            start_date=start_date,
            end_date=end_date,
            organization_id=organization_id
        )
        
        if format == "csv":
            # Convert to CSV format
            from io import StringIO
            import csv
            from fastapi.responses import StreamingResponse
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(["Date", "Revenue", "Orders", "Customers"])
            
            # Write data
            for row in trend_data:
                writer.writerow([
                    row["date"],
                    row["revenue"],
                    row["orders"],
                    row["customers"]
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=revenue_report.csv"}
            )
        
        else:
            # Return JSON format
            return {
                "report": {
                    "overview": overview,
                    "daily_data": trend_data
                },
                "metadata": {
                    "exported_at": "2025-08-20T18:00:00Z",
                    "format": format,
                    "filters": {
                        "date_range": date_range,
                        "organization_id": organization_id
                    }
                }
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export revenue report: {str(e)}")


@router.get("/metrics/summary")
async def get_metrics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get high-level metrics summary for quick overview (admin only)
    """
    try:
        from sqlalchemy import select, func
        from app.models.event import Event
        from app.models.user import User
        from app.models.order import Order
        from app.models.organization import Organization
        
        # Get basic counts
        total_users = await db.scalar(select(func.count(User.id)))
        total_events = await db.scalar(select(func.count(Event.id)))
        total_orders = await db.scalar(select(func.count(Order.id)))
        total_organizations = await db.scalar(select(func.count(Organization.id)))
        
        # Revenue
        total_revenue = await db.scalar(
            select(func.sum(Order.total_amount)).where(Order.status == "completed")
        ) or 0
        
        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        new_users_week = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
        new_orders_week = await db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= week_ago)
        )
        
        return {
            "summary": {
                "totals": {
                    "users": total_users or 0,
                    "events": total_events or 0,
                    "orders": total_orders or 0,
                    "organizations": total_organizations or 0,
                    "revenue": float(total_revenue)
                },
                "recent_activity": {
                    "new_users_7d": new_users_week or 0,
                    "new_orders_7d": new_orders_week or 0
                }
            },
            "generated_at": "2025-08-20T18:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics summary: {str(e)}")