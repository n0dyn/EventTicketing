"""
Waitlist Management API Endpoints
REST API for managing event waitlists and user waitlist entries
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.waitlist import (
    EventWaitlist, EventWaitlistCreate, EventWaitlistUpdate,
    WaitlistEntry, WaitlistEntryCreate, WaitlistEntryUpdate, WaitlistEntryWithUser,
    WaitlistNotification, WaitlistRelease, WaitlistReleaseCreate,
    WaitlistPreferences, WaitlistPreferencesUpdate,
    WaitlistPosition, WaitlistStats, BulkWaitlistOperation, BulkWaitlistResult
)
from app.services.waitlist import waitlist_service

router = APIRouter()


# Event Waitlist Management Endpoints

@router.post("/events/{event_id}/waitlist", response_model=EventWaitlist, status_code=status.HTTP_201_CREATED)
async def create_event_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    waitlist_data: EventWaitlistCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a waitlist for an event"""
    # Ensure event_id matches
    waitlist_data.event_id = event_id
    
    try:
        waitlist = await waitlist_service.create_event_waitlist(
            db=db, 
            waitlist_data=waitlist_data, 
            user_id=current_user.id
        )
        return waitlist
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events/{event_id}/waitlist", response_model=EventWaitlist)
async def get_event_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get waitlist information for an event"""
    waitlist = await waitlist_service.get_event_waitlist(db=db, event_id=event_id)
    if not waitlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found for this event"
        )
    return waitlist


@router.put("/events/{event_id}/waitlist", response_model=EventWaitlist)
async def update_event_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    waitlist_data: EventWaitlistUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update waitlist settings for an event"""
    waitlist = await waitlist_service.update_event_waitlist(
        db=db, 
        event_id=event_id, 
        waitlist_data=waitlist_data, 
        user_id=current_user.id
    )
    if not waitlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist not found or access denied"
        )
    return waitlist


# Waitlist Entry Management Endpoints

@router.post("/events/{event_id}/waitlist/join", response_model=WaitlistEntry, status_code=status.HTTP_201_CREATED)
async def join_event_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    entry_data: WaitlistEntryCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Join an event waitlist"""
    # Ensure event_id matches
    entry_data.event_id = event_id
    
    try:
        entry = await waitlist_service.join_waitlist(
            db=db, 
            entry_data=entry_data, 
            user_id=current_user.id
        )
        return entry
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/events/{event_id}/waitlist/position", response_model=WaitlistPosition)
async def get_waitlist_position(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get user's position in event waitlist"""
    position = await waitlist_service.get_user_waitlist_position(
        db=db, 
        event_id=event_id, 
        user_id=current_user.id
    )
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found on waitlist for this event"
        )
    return position


@router.put("/waitlist/entries/{entry_id}", response_model=WaitlistEntry)
async def update_waitlist_entry(
    *,
    db: AsyncSession = Depends(get_db),
    entry_id: int,
    entry_data: WaitlistEntryUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update user's waitlist entry"""
    entry = await waitlist_service.update_waitlist_entry(
        db=db, 
        entry_id=entry_id, 
        entry_data=entry_data, 
        user_id=current_user.id
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found"
        )
    return entry


@router.delete("/waitlist/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def leave_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    entry_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Leave an event waitlist"""
    success = await waitlist_service.leave_waitlist(
        db=db, 
        entry_id=entry_id, 
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found or already inactive"
        )


@router.get("/waitlist/entries/{entry_id}", response_model=WaitlistEntry)
async def get_waitlist_entry(
    *,
    db: AsyncSession = Depends(get_db),
    entry_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Get specific waitlist entry"""
    entry = await waitlist_service.get_waitlist_entry(
        db=db, 
        entry_id=entry_id, 
        user_id=current_user.id
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found"
        )
    return entry


# User Waitlist Management

@router.get("/users/me/waitlist", response_model=List[WaitlistEntry])
async def get_user_waitlist_entries(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    active_only: bool = Query(True, description="Only return active waitlist entries"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get all waitlist entries for the current user"""
    from sqlalchemy import select, and_
    from app.models.waitlist import WaitlistEntry, WaitlistStatus
    
    query = select(WaitlistEntry).where(WaitlistEntry.user_id == current_user.id)
    
    if active_only:
        query = query.where(WaitlistEntry.status == WaitlistStatus.ACTIVE.value)
    
    query = query.offset(skip).limit(limit).order_by(WaitlistEntry.joined_at.desc())
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return entries


# User Preferences Endpoints

@router.get("/users/me/waitlist/preferences", response_model=WaitlistPreferences)
async def get_user_waitlist_preferences(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's waitlist preferences"""
    preferences = await waitlist_service.get_user_preferences(db=db, user_id=current_user.id)
    if not preferences:
        # Return default preferences
        from app.schemas.waitlist import WaitlistPreferencesUpdate
        default_prefs = WaitlistPreferencesUpdate()
        preferences = await waitlist_service.update_user_preferences(
            db=db, 
            user_id=current_user.id, 
            preferences_data=default_prefs
        )
    return preferences


@router.put("/users/me/waitlist/preferences", response_model=WaitlistPreferences)
async def update_user_waitlist_preferences(
    *,
    db: AsyncSession = Depends(get_db),
    preferences_data: WaitlistPreferencesUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update user's waitlist preferences"""
    preferences = await waitlist_service.update_user_preferences(
        db=db, 
        user_id=current_user.id, 
        preferences_data=preferences_data
    )
    return preferences


# Admin/Organizer Endpoints

@router.get("/events/{event_id}/waitlist/entries", response_model=List[WaitlistEntryWithUser])
async def get_event_waitlist_entries(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    current_user: User = Depends(get_current_active_user),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get all waitlist entries for an event (organizer only)"""
    from sqlalchemy import select, and_
    from sqlalchemy.orm import joinedload
    from app.models.waitlist import WaitlistEntry
    from app.models.event import Event
    
    # Verify event ownership
    event_query = select(Event).where(
        and_(Event.id == event_id, Event.owner_id == current_user.id)
    )
    result = await db.execute(event_query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied or event not found"
        )
    
    # Get waitlist entries
    query = select(WaitlistEntry).options(
        joinedload(WaitlistEntry.user)
    ).where(WaitlistEntry.event_id == event_id)
    
    if status_filter:
        query = query.where(WaitlistEntry.status == status_filter)
    
    if priority_filter:
        query = query.where(WaitlistEntry.priority == priority_filter)
    
    query = query.offset(skip).limit(limit).order_by(WaitlistEntry.position)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    return entries


@router.post("/events/{event_id}/waitlist/release", response_model=WaitlistRelease, status_code=status.HTTP_201_CREATED)
async def release_tickets_to_waitlist(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    release_data: WaitlistReleaseCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Release tickets to waitlist (organizer only)"""
    # Ensure event_id matches
    release_data.event_id = event_id
    
    try:
        release = await waitlist_service.process_ticket_release(
            db=db, 
            release_data=release_data, 
            user_id=current_user.id
        )
        return release
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/events/{event_id}/waitlist/bulk", response_model=BulkWaitlistResult)
async def bulk_waitlist_operation(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    operation_data: BulkWaitlistOperation,
    current_user: User = Depends(get_current_active_user)
):
    """Perform bulk operations on waitlist entries (organizer only)"""
    from sqlalchemy import select, and_, update
    from app.models.waitlist import WaitlistEntry
    from app.models.event import Event
    
    # Verify event ownership
    event_query = select(Event).where(
        and_(Event.id == event_id, Event.owner_id == current_user.id)
    )
    result = await db.execute(event_query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied or event not found"
        )
    
    # Get targeted entries
    entries_query = select(WaitlistEntry).where(
        and_(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.id.in_(operation_data.entry_ids)
        )
    )
    result = await db.execute(entries_query)
    entries = result.scalars().all()
    
    successful = 0
    failed = 0
    errors = []
    processed_ids = []
    
    for entry in entries:
        try:
            if operation_data.operation == "notify":
                # Create manual notification
                # This would trigger the notification process
                processed_ids.append(entry.id)
                successful += 1
            elif operation_data.operation == "cancel":
                entry.status = "cancelled"
                processed_ids.append(entry.id)
                successful += 1
            elif operation_data.operation == "promote":
                # Increase priority
                entry.priority_score = min(entry.priority_score + 5.0, 100.0)
                processed_ids.append(entry.id)
                successful += 1
            elif operation_data.operation == "demote":
                # Decrease priority
                entry.priority_score = max(entry.priority_score - 5.0, 0.0)
                processed_ids.append(entry.id)
                successful += 1
        except Exception as e:
            failed += 1
            errors.append(f"Entry {entry.id}: {str(e)}")
    
    await db.commit()
    
    return BulkWaitlistResult(
        operation=operation_data.operation,
        total_requested=len(operation_data.entry_ids),
        successful=successful,
        failed=failed,
        errors=errors,
        processed_entry_ids=processed_ids
    )


# Statistics and Analytics

@router.get("/events/{event_id}/waitlist/stats", response_model=WaitlistStats)
async def get_event_waitlist_stats(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get waitlist statistics for an event"""
    from sqlalchemy import select, func, and_
    from app.models.waitlist import WaitlistEntry, EventWaitlist, WaitlistStatus
    from app.models.event import Event
    
    # Check if user can view stats (event owner or user on waitlist)
    event_query = select(Event).where(Event.id == event_id)
    result = await db.execute(event_query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # If not owner, check if user is on waitlist
    if event.owner_id != current_user.id:
        user_entry_query = select(WaitlistEntry).where(
            and_(
                WaitlistEntry.event_id == event_id,
                WaitlistEntry.user_id == current_user.id
            )
        )
        result = await db.execute(user_entry_query)
        user_entry = result.scalar_one_or_none()
        
        if not user_entry:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get waitlist
    waitlist = await waitlist_service.get_event_waitlist(db=db, event_id=event_id)
    
    if not waitlist:
        return WaitlistStats(
            event_id=event_id,
            waitlist_enabled=False,
            total_entries=0,
            active_entries=0,
            average_position=0,
            estimated_wait_time_hours=0,
            conversion_rate=0,
            latest_activity=None
        )
    
    # Get statistics
    stats_query = select(
        func.count(WaitlistEntry.id).label("total"),
        func.count(WaitlistEntry.id).filter(WaitlistEntry.status == WaitlistStatus.ACTIVE.value).label("active"),
        func.avg(WaitlistEntry.position).label("avg_position"),
        func.max(WaitlistEntry.updated_at).label("latest_activity")
    ).where(WaitlistEntry.event_id == event_id)
    
    result = await db.execute(stats_query)
    stats = result.first()
    
    return WaitlistStats(
        event_id=event_id,
        waitlist_enabled=waitlist.is_enabled,
        total_entries=stats.total or 0,
        active_entries=stats.active or 0,
        average_position=float(stats.avg_position or 0),
        estimated_wait_time_hours=24.0,  # Simplified calculation
        conversion_rate=waitlist.conversion_rate,
        latest_activity=stats.latest_activity
    )