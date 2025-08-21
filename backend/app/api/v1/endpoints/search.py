"""
Search and filtering endpoints
"""
from typing import Any, Dict, List, Optional
from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.search_service import (
    event_search, 
    user_search, 
    analytics_search,
    EventSortField,
    SortOrder
)
from app.schemas.event import EventResponse
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/events")
async def search_events(
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query"),
    category_ids: Optional[List[int]] = Query(None, description="Category IDs to filter by"),
    organization_ids: Optional[List[int]] = Query(None, description="Organization IDs to filter by"),
    location: Optional[str] = Query(None, description="Location to search in"),
    start_date: Optional[date] = Query(None, description="Events starting after this date"),
    end_date: Optional[date] = Query(None, description="Events starting before this date"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum ticket price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum ticket price"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    has_tickets_available: Optional[bool] = Query(None, description="Filter events with available tickets"),
    sort_by: EventSortField = Query(EventSortField.START_DATE, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.ASC, description="Sort order"),
    page: int = Query(0, ge=0, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
) -> Dict[str, Any]:
    """
    Search events with advanced filtering and sorting
    """
    try:
        events, total = await event_search.search_events(
            db=db,
            query=q,
            category_ids=category_ids,
            organization_ids=organization_ids,
            location=location,
            start_date=start_date,
            end_date=end_date,
            min_price=min_price,
            max_price=max_price,
            is_active=is_active,
            has_tickets_available=has_tickets_available,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        return {
            "events": events,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": (page + 1) * page_size < total,
                "has_prev": page > 0
            },
            "filters_applied": {
                "query": q,
                "category_ids": category_ids,
                "organization_ids": organization_ids,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "price_range": [min_price, max_price] if min_price or max_price else None,
                "is_active": is_active,
                "has_tickets_available": has_tickets_available
            },
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/events/suggestions")
async def get_search_suggestions(
    db: AsyncSession = Depends(get_db),
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions")
) -> Dict[str, List[str]]:
    """
    Get search suggestions for autocomplete
    """
    try:
        suggestions = await event_search.get_search_suggestions(
            db=db,
            query=q,
            limit=limit
        )
        
        return suggestions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/events/popular")
async def get_popular_searches(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of popular searches")
) -> Dict[str, List[str]]:
    """
    Get popular search terms
    """
    try:
        popular_searches = await event_search.get_popular_searches(
            db=db,
            limit=limit
        )
        
        return {"popular_searches": popular_searches}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular searches: {str(e)}")


@router.get("/users")
async def search_users(
    db: AsyncSession = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query (name, email)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_superuser: Optional[bool] = Query(None, description="Filter by superuser status"),
    has_orders: Optional[bool] = Query(None, description="Filter users with/without orders"),
    registration_start: Optional[date] = Query(None, description="Users registered after this date"),
    registration_end: Optional[date] = Query(None, description="Users registered before this date"),
    sort_by: str = Query("created_at", regex="^(created_at|email|full_name)$", description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    page: int = Query(0, ge=0, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size")
) -> Dict[str, Any]:
    """
    Search users with filtering (admin functionality would require authentication)
    """
    try:
        users, total = await user_search.search_users(
            db=db,
            query=q,
            is_active=is_active,
            is_superuser=is_superuser,
            has_orders=has_orders,
            registration_start=registration_start,
            registration_end=registration_end,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        return {
            "users": users,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": (page + 1) * page_size < total,
                "has_prev": page > 0
            },
            "filters_applied": {
                "query": q,
                "is_active": is_active,
                "is_superuser": is_superuser,
                "has_orders": has_orders,
                "registration_period": [registration_start, registration_end] if registration_start or registration_end else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User search failed: {str(e)}")


@router.get("/analytics/events")
async def get_event_analytics(
    db: AsyncSession = Depends(get_db),
    event_id: Optional[int] = Query(None, description="Specific event ID"),
    organization_id: Optional[int] = Query(None, description="Organization ID"),
    start_date: Optional[date] = Query(None, description="Analytics start date"),
    end_date: Optional[date] = Query(None, description="Analytics end date")
) -> Dict[str, Any]:
    """
    Get event analytics with filtering
    """
    try:
        analytics = await analytics_search.get_event_analytics(
            db=db,
            event_id=event_id,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "analytics": analytics,
            "filters": {
                "event_id": event_id,
                "organization_id": organization_id,
                "date_range": [start_date, end_date] if start_date or end_date else None
            },
            "generated_at": "2025-08-20T18:00:00Z"  # In production, use datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics query failed: {str(e)}")


@router.get("/facets")
async def get_search_facets(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get search facets for filtering UI
    """
    try:
        # Get available categories
        from app.models.event_category import EventCategory
        from sqlalchemy import select
        
        categories = await db.execute(
            select(EventCategory.id, EventCategory.name)
            .order_by(EventCategory.name)
        )
        
        # Get available organizations
        from app.models.organization import Organization
        organizations = await db.execute(
            select(Organization.id, Organization.name)
            .order_by(Organization.name)
        )
        
        # Get available locations (top 20)
        locations = await db.execute(
            select(Event.location)
            .where(Event.location.is_not(None))
            .group_by(Event.location)
            .order_by(func.count(Event.id).desc())
            .limit(20)
        )
        
        # Get price ranges
        from sqlalchemy import func
        price_stats = await db.execute(
            select(
                func.min(Ticket.price).label("min_price"),
                func.max(Ticket.price).label("max_price"),
                func.avg(Ticket.price).label("avg_price")
            )
            .join(Event)
            .where(Event.is_active == True)
        )
        
        price_row = price_stats.first()
        
        return {
            "categories": [
                {"id": cat.id, "name": cat.name}
                for cat in categories
            ],
            "organizations": [
                {"id": org.id, "name": org.name}
                for org in organizations
            ],
            "locations": [loc[0] for loc in locations if loc[0]],
            "price_range": {
                "min": float(price_row.min_price or 0) if price_row else 0,
                "max": float(price_row.max_price or 1000) if price_row else 1000,
                "average": float(price_row.avg_price or 0) if price_row else 0
            },
            "sort_options": [
                {"value": "start_date", "label": "Event Date"},
                {"value": "created_at", "label": "Recently Added"},
                {"value": "title", "label": "Event Title"},
                {"value": "price", "label": "Price"},
                {"value": "popularity", "label": "Popularity"}
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get search facets: {str(e)}")