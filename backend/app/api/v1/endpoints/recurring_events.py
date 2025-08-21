"""
Recurring Events API Endpoints
REST API for managing recurring events and event series
"""

from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.recurring_event import (
    EventSeries, EventSeriesCreate, EventSeriesUpdate,
    EventInstance, EventInstanceCreate, EventInstanceUpdate,
    RecurrencePreview, BulkEventOperation, BulkEventResult,
    EventWithSeries
)
from app.schemas.event import Event as EventSchema
from app.services.recurring_event import recurring_event_service

router = APIRouter()


# Event Series Endpoints

@router.get("/series", response_model=List[EventSeries])
async def get_user_event_series(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True)
):
    """Get all event series for the current user"""
    series_list = await recurring_event_service.get_user_event_series(
        db=db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit,
        active_only=active_only
    )
    return series_list


@router.post("/series", response_model=EventSeries, status_code=status.HTTP_201_CREATED)
async def create_event_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_data: EventSeriesCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new recurring event series"""
    try:
        series = await recurring_event_service.create_event_series(
            db=db, 
            series_data=series_data, 
            user_id=current_user.id
        )
        return series
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create event series: {str(e)}"
        )


@router.get("/series/{series_id}", response_model=EventSeries)
async def get_event_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific event series"""
    series = await recurring_event_service.get_event_series(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id
    )
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event series not found"
        )
    return series


@router.put("/series/{series_id}", response_model=EventSeries)
async def update_event_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    series_data: EventSeriesUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update an event series"""
    series = await recurring_event_service.update_event_series(
        db=db, 
        series_id=series_id, 
        series_data=series_data, 
        user_id=current_user.id
    )
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event series not found"
        )
    return series


@router.delete("/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user),
    delete_events: bool = Query(True, description="Delete all events in the series")
):
    """Delete an event series"""
    success = await recurring_event_service.delete_event_series(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id,
        delete_events=delete_events
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event series not found"
        )


# Event Generation Endpoints

@router.post("/series/{series_id}/generate", response_model=List[EventSchema])
async def generate_events_for_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user),
    days_ahead: Optional[int] = Query(None, ge=1, le=365, description="Days to generate events for")
):
    """Generate new events for a series"""
    events = await recurring_event_service.generate_events_for_series(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id,
        days_ahead=days_ahead
    )
    return events


@router.post("/series/{series_id}/regenerate", response_model=List[EventSchema])
async def regenerate_events_for_series(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Regenerate all future events for a series"""
    events = await recurring_event_service.regenerate_events_for_series(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id
    )
    return events


@router.get("/series/{series_id}/events", response_model=List[EventWithSeries])
async def get_series_events(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user),
    include_past: bool = Query(False, description="Include past events"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all events in a series"""
    events = await recurring_event_service.get_series_events(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id,
        include_past=include_past,
        skip=skip, 
        limit=limit
    )
    return events


# Recurrence Preview Endpoints

@router.post("/preview", response_model=RecurrencePreview)
async def preview_recurrence_dates(
    *,
    pattern_data: dict,
    start_date: date,
    preview_count: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Preview dates that would be generated by a recurrence pattern"""
    from app.schemas.recurring_event import RecurrencePatternCreate
    
    try:
        pattern = RecurrencePatternCreate(**pattern_data)
        preview = await recurring_event_service.preview_recurrence_dates(
            pattern_data=pattern,
            start_date=start_date,
            preview_count=preview_count
        )
        return preview
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recurrence pattern: {str(e)}"
        )


# Event Instance Customization Endpoints

@router.post("/events/{event_id}/customize", response_model=EventInstance, status_code=status.HTTP_201_CREATED)
async def create_event_instance_customization(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    instance_data: EventInstanceCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create customizations for a recurring event instance"""
    # Ensure the event_id matches
    instance_data.event_id = event_id
    
    instance = await recurring_event_service.create_event_instance(
        db=db, 
        instance_data=instance_data, 
        user_id=current_user.id
    )
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or not part of a series"
        )
    return instance


@router.get("/events/{event_id}/customize", response_model=EventInstance)
async def get_event_instance_customization(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get customizations for a recurring event instance"""
    instance = await recurring_event_service.get_event_instance(
        db=db, 
        event_id=event_id, 
        user_id=current_user.id
    )
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event instance customizations not found"
        )
    return instance


@router.put("/events/{event_id}/customize", response_model=EventInstance)
async def update_event_instance_customization(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    instance_data: EventInstanceUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update customizations for a recurring event instance"""
    instance = await recurring_event_service.update_event_instance(
        db=db, 
        event_id=event_id, 
        instance_data=instance_data, 
        user_id=current_user.id
    )
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event instance customizations not found"
        )
    return instance


# Bulk Operations

@router.post("/series/{series_id}/bulk", response_model=BulkEventResult)
async def bulk_operation_on_series_events(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    operation_data: BulkEventOperation,
    current_user: User = Depends(get_current_active_user)
):
    """Perform bulk operations on events in a series"""
    result = await recurring_event_service.bulk_operation_on_series_events(
        db=db, 
        series_id=series_id, 
        operation_data=operation_data, 
        user_id=current_user.id
    )
    return result


# Statistics and Analytics

@router.get("/series/{series_id}/stats")
async def get_series_statistics(
    *,
    db: AsyncSession = Depends(get_db),
    series_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics for an event series"""
    series = await recurring_event_service.get_event_series(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id
    )
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event series not found"
        )
    
    events = await recurring_event_service.get_series_events(
        db=db, 
        series_id=series_id, 
        user_id=current_user.id,
        include_past=True,
        limit=1000  # Get all events for stats
    )
    
    from datetime import datetime
    now = datetime.utcnow()
    
    stats = {
        "series_id": series_id,
        "total_events": len(events),
        "upcoming_events": len([e for e in events if e.start_time > now]),
        "past_events": len([e for e in events if e.start_time <= now]),
        "published_events": len([e for e in events if e.status == "published"]),
        "cancelled_events": len([e for e in events if e.status == "cancelled"]),
        "customized_events": len([e for e in events if e.event_instance]),
        "series_info": {
            "title": series.title,
            "is_active": series.is_active,
            "auto_publish": series.auto_publish,
            "recurrence_type": series.recurrence_pattern.recurrence_type,
            "created_at": series.created_at,
            "updated_at": series.updated_at
        }
    }
    
    return stats