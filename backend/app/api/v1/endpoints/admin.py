"""
Admin dashboard endpoints
"""
from typing import Any, Dict, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_superuser
from app.models.user import User
from app.models.event import Event
from app.models.order import Order, OrderStatus
from app.models.payment import Payment
from app.models.organization import Organization
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.event import EventResponse
from app.schemas.organization import Organization as OrganizationSchema
from app.services.user import get_user_by_id, update_user

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get dashboard statistics for admin
    """
    try:
        # Basic counts
        total_users = await db.scalar(select(func.count(User.id)))
        total_events = await db.scalar(select(func.count(Event.id)))
        total_orders = await db.scalar(select(func.count(Order.id)))
        total_organizations = await db.scalar(select(func.count(Organization.id)))
        
        # Revenue stats
        total_revenue = await db.scalar(
            select(func.sum(Order.total_amount)).where(Order.status == OrderStatus.COMPLETED)
        ) or 0
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        new_users_30d = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
        )
        new_events_30d = await db.scalar(
            select(func.count(Event.id)).where(Event.created_at >= thirty_days_ago)
        )
        new_orders_30d = await db.scalar(
            select(func.count(Order.id)).where(Order.created_at >= thirty_days_ago)
        )
        revenue_30d = await db.scalar(
            select(func.sum(Order.total_amount)).where(
                and_(Order.created_at >= thirty_days_ago, Order.status == OrderStatus.COMPLETED)
            )
        ) or 0
        
        # Active events
        active_events = await db.scalar(
            select(func.count(Event.id)).where(
                and_(Event.is_active == True, Event.start_time > datetime.utcnow())
            )
        )
        
        # Top events by orders
        top_events_result = await db.execute(
            select(Event.title, func.count(Order.id).label("order_count"))
            .join(Order, Event.id == Order.event_id)
            .group_by(Event.id, Event.title)
            .order_by(func.count(Order.id).desc())
            .limit(5)
        )
        top_events = [{"title": row[0], "orders": row[1]} for row in top_events_result]
        
        return {
            "overview": {
                "total_users": total_users,
                "total_events": total_events,
                "total_orders": total_orders,
                "total_organizations": total_organizations,
                "total_revenue": float(total_revenue),
                "active_events": active_events
            },
            "recent_activity": {
                "new_users_30d": new_users_30d,
                "new_events_30d": new_events_30d,
                "new_orders_30d": new_orders_30d,
                "revenue_30d": float(revenue_30d)
            },
            "top_events": top_events,
            "updated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, le=1000),  # Return all users for admin interface
    search: str = Query("", description="Search by name or email"),
    is_active: bool = Query(None, description="Filter by active status"),
    is_superuser: bool = Query(None, description="Filter by superuser status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> List[UserResponse]:
    """
    List users with filtering (admin only) - returns simple array for frontend
    """
    try:
        # Build query
        query = select(User)
        
        # Add search filter
        if search:
            search_filter = or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Add status filters
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if is_superuser is not None:
            query = query.where(User.is_superuser == is_superuser)
        
        # Apply ordering and execute
        query = query.order_by(User.created_at.desc()).limit(limit).offset(skip)
        result = await db.execute(query)
        users = result.scalars().all()
        
        return users
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.put("/users/{user_id}")
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> UserResponse:
    """
    Update user (admin only)
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated_user = await update_user(db, user, user_update)
    await db.commit()
    await db.refresh(updated_user)
    
    return updated_user


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, str]:
    """
    Delete user (admin only)
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/events")
async def list_events_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, le=1000),  # Return all events for admin interface
    search: str = Query("", description="Search by title"),
    is_active: bool = Query(None, description="Filter by active status"),
    organization_id: int = Query(None, description="Filter by organization"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> List[EventResponse]:
    """
    List events with filtering (admin only) - returns simple array for frontend
    """
    try:
        # Build query
        query = select(Event).options(
            selectinload(Event.organization),
            selectinload(Event.owner)
        )
        
        # Add search filter
        if search:
            query = query.where(Event.title.ilike(f"%{search}%"))
        
        # Add filters
        if is_active is not None:
            query = query.where(Event.is_active == is_active)
        if organization_id is not None:
            query = query.where(Event.organization_id == organization_id)
        
        # Apply ordering and execute
        query = query.order_by(Event.created_at.desc()).limit(limit).offset(skip)
        result = await db.execute(query)
        events = result.scalars().all()
        
        return events
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list events: {str(e)}")


@router.put("/events/{event_id}")
async def update_event_admin(
    event_id: int,
    update_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> EventResponse:
    """
    Update event fields (admin only)
    """
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Update allowed fields
    for field, value in update_data.items():
        if field in ['is_active', 'is_public', 'title', 'description', 'status']:
            setattr(event, field, value)
    
    event.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(event)
    
    return event


@router.put("/events/{event_id}/status")
async def update_event_status(
    event_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Update event active status (admin only)
    """
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_active = is_active
    event.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(event)
    
    return {
        "message": f"Event {'activated' if is_active else 'deactivated'} successfully",
        "event": event
    }


@router.get("/orders")
async def list_orders_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: str = Query(None, description="Filter by order status"),
    user_id: int = Query(None, description="Filter by user"),
    event_id: int = Query(None, description="Filter by event"),
    start_date: datetime = Query(None, description="Filter orders after this date"),
    end_date: datetime = Query(None, description="Filter orders before this date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    List orders with filtering and pagination (admin only)
    """
    try:
        # Build query
        query = select(Order).options(
            selectinload(Order.user),
            selectinload(Order.event),
            selectinload(Order.payments)
        )
        
        # Add filters
        if status:
            query = query.where(Order.status == status)
        if user_id:
            query = query.where(Order.user_id == user_id)
        if event_id:
            query = query.where(Order.event_id == event_id)
        if start_date:
            query = query.where(Order.created_at >= start_date)
        if end_date:
            query = query.where(Order.created_at <= end_date)
        
        # Get total count
        count_query = select(func.count(Order.id))
        if status:
            count_query = count_query.where(Order.status == status)
        if user_id:
            count_query = count_query.where(Order.user_id == user_id)
        if event_id:
            count_query = count_query.where(Order.event_id == event_id)
        if start_date:
            count_query = count_query.where(Order.created_at >= start_date)
        if end_date:
            count_query = count_query.where(Order.created_at <= end_date)
        
        total = await db.scalar(count_query)
        
        # Apply pagination and ordering
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return {
            "orders": orders,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + limit < total
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orders: {str(e)}")


@router.get("/analytics/revenue")
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get revenue analytics for the specified period
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily revenue
        daily_revenue_result = await db.execute(
            select(
                func.date(Order.created_at).label("date"),
                func.sum(Order.total_amount).label("revenue"),
                func.count(Order.id).label("orders")
            )
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.status == "completed"
                )
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        
        daily_revenue = [
            {
                "date": row[0].isoformat(),
                "revenue": float(row[1] or 0),
                "orders": row[2]
            }
            for row in daily_revenue_result
        ]
        
        # Total revenue for period
        total_revenue = await db.scalar(
            select(func.sum(Order.total_amount)).where(
                and_(
                    Order.created_at >= start_date,
                    Order.status == "completed"
                )
            )
        ) or 0
        
        # Average order value
        avg_order_value = await db.scalar(
            select(func.avg(Order.total_amount)).where(
                and_(
                    Order.created_at >= start_date,
                    Order.status == "completed"
                )
            )
        ) or 0
        
        return {
            "period_days": days,
            "start_date": start_date,
            "total_revenue": float(total_revenue),
            "average_order_value": float(avg_order_value),
            "daily_revenue": daily_revenue
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get revenue analytics: {str(e)}")


@router.get("/system/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get system health information
    """
    try:
        # Database health check
        db_healthy = True
        try:
            await db.execute(select(1))
        except Exception:
            db_healthy = False
        
        # Basic system stats
        uptime = datetime.utcnow()  # This would be actual uptime in production
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": datetime.utcnow(),
            "uptime": uptime.isoformat(),
            "services": {
                "api": "running",
                "database": "connected" if db_healthy else "disconnected",
                "email": "configured",  # You could check email service here
                "file_storage": "configured"  # You could check file storage here
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }


@router.get("/organizations")
async def list_organizations_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, le=1000),  # Return all organizations for admin interface
    search: str = Query("", description="Search by name"),
    is_active: bool = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> List[Dict[str, Any]]:
    """
    List organizations with filtering (admin only) - returns simple array for frontend
    """
    try:
        # Build query - select only existing columns
        query = select(
            Organization.id,
            Organization.name,
            Organization.description,
            Organization.website,
            Organization.logo_url,
            Organization.is_active,
            Organization.created_at,
            Organization.updated_at
        )
        
        # Add search filter
        if search:
            search_filter = or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Add status filters
        if is_active is not None:
            query = query.where(Organization.is_active == is_active)
        
        # Apply ordering and execute
        query = query.order_by(Organization.created_at.desc()).limit(limit).offset(skip)
        result = await db.execute(query)
        organizations = result.scalars().all()
        
        # Get additional stats for each organization
        org_data = []
        for org in organizations:
            # Count members for this organization (using many-to-many relationship)
            from app.models.user import user_organization
            member_count = await db.scalar(
                select(func.count()).select_from(user_organization).where(user_organization.c.organization_id == org.id)
            ) or 0
            
            event_count = await db.scalar(
                select(func.count(Event.id)).where(Event.organization_id == org.id)
            ) or 0
            
            org_dict = {
                "id": str(org.id),
                "name": org.name,
                "slug": org.name.lower().replace(' ', '-') if org.name else '',  # Generate slug from name
                "description": org.description,
                "website": org.website,
                "logo_url": org.logo_url,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat(),
                "updated_at": org.updated_at.isoformat(),
                "member_count": member_count,
                "event_count": event_count
            }
            org_data.append(org_dict)
        
        return org_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list organizations: {str(e)}")


@router.put("/organizations/{org_id}")
async def update_organization_admin(
    org_id: int,
    update_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Update organization fields (admin only)
    """
    organization = await db.get(Organization, org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Update allowed fields
    for field, value in update_data.items():
        if field in ['is_active', 'name', 'description', 'website']:
            setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(organization)
    
    return {
        "id": str(organization.id),
        "name": organization.name,
        "slug": organization.name.lower().replace(' ', '-') if organization.name else '',
        "description": organization.description,
        "website": organization.website,
        "logo_url": organization.logo_url,
        "is_active": organization.is_active,
        "created_at": organization.created_at.isoformat(),
        "updated_at": organization.updated_at.isoformat()
    }