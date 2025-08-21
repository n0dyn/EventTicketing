from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, Event as EventSchema
from app.services.event import event_service
from app.core.caching import RequestCache, CacheInvalidator, cached

router = APIRouter()


@router.get("/public", response_model=List[EventSchema])
async def read_public_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
) -> Any:
    """
    Retrieve public events (no authentication required).
    """
    # Check cache first
    cached_response = await RequestCache.get_cached_response(
        request, {"user_type": "public"}
    )
    if cached_response is not None:
        return cached_response
    
    events = await event_service.get_public_events(
        db, skip=skip, limit=limit, search=search, category_id=category_id
    )
    
    # Cache for 5 minutes
    await RequestCache.set_cached_response(
        request, events, ttl=300, additional_params={"user_type": "public"}
    )
    
    return events


@router.get("/", response_model=List[EventSchema])
async def read_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
) -> Any:
    """
    Retrieve events for authenticated user.
    """
    # Check cache first
    cached_response = await RequestCache.get_cached_response(
        request, {"user_id": current_user.id, "is_superuser": current_user.is_superuser}
    )
    if cached_response is not None:
        return cached_response
    
    events = await event_service.get_multi(
        db, skip=skip, limit=limit, search=search, category_id=category_id, 
        user_id=current_user.id if not current_user.is_superuser else None
    )
    
    # Cache for 2 minutes (shorter for user-specific data)
    await RequestCache.set_cached_response(
        request, events, ttl=120, 
        additional_params={"user_id": current_user.id, "is_superuser": current_user.is_superuser}
    )
    
    return events


@router.post("/", response_model=EventSchema)
async def create_event(
    *,
    db: AsyncSession = Depends(get_db),
    event_in: EventCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create new event.
    """
    event = await event_service.create(db=db, obj_in=event_in, owner_id=current_user.id)
    
    # Invalidate related caches
    await CacheInvalidator.invalidate_event_cache(event.id)
    
    return event


@router.get("/{id}", response_model=EventSchema)
@cached(ttl=300, key_prefix="event_detail")
async def read_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get event by ID.
    """
    event = await event_service.get(db=db, id=id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return event


@router.put("/{id}", response_model=EventSchema)
async def update_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    event_in: EventUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update an event.
    """
    event = await event_service.get(db=db, id=id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    event = await event_service.update(db=db, db_obj=event, obj_in=event_in)
    
    # Invalidate related caches
    await CacheInvalidator.invalidate_event_cache(int(id))
    
    return event


@router.delete("/{id}", response_model=EventSchema)
async def delete_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete an event.
    """
    event = await event_service.get(db=db, id=id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Invalidate related caches before deletion
    await CacheInvalidator.invalidate_event_cache(int(id))
    
    event = await event_service.remove(db=db, id=id)
    return event


@router.post("/{id}/publish", response_model=EventSchema)
async def publish_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Publish an event.
    """
    event = await event_service.get(db=db, id=id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    event = await event_service.publish(db=db, db_obj=event)
    return event


@router.post("/{id}/unpublish", response_model=EventSchema)
async def unpublish_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Unpublish an event.
    """
    event = await event_service.get(db=db, id=id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    event = await event_service.unpublish(db=db, db_obj=event)
    return event 