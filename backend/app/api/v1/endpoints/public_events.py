from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.event import Event, EventStatus
from app.schemas.event import Event as EventSchema
from app.services.event import event_service

router = APIRouter()


@router.get("/", response_model=List[EventSchema])
async def get_public_events(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_free: Optional[bool] = None,
) -> Any:
    """
    Get all public published events.
    """
    events = await event_service.get_public_events(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        location=location,
        start_date=start_date,
        end_date=end_date,
        is_free=is_free,
    )
    return events


@router.get("/{event_id}", response_model=EventSchema)
async def get_public_event(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
) -> Any:
    """
    Get a specific public event by ID.
    """
    event = await event_service.get_public_event(db=db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or not public"
        )
    return event


@router.get("/{event_id}/tickets", response_model=List[dict])
async def get_event_tickets(
    *,
    db: AsyncSession = Depends(get_db),
    event_id: str,
) -> Any:
    """
    Get available ticket types for a public event.
    """
    from app.services.ticket import ticket_service
    
    event = await event_service.get_public_event(db=db, id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found or not public"
        )
    
    ticket_types = await ticket_service.get_by_event(
        db=db, event_id=event_id, only_active=True
    )
    
    return [
        {
            "id": tt.id,
            "name": tt.name,
            "description": tt.description,
            "price": tt.price,
            "quantity_total": tt.quantity_total,
            "quantity_sold": tt.quantity_sold,
            "quantity_available": tt.quantity_total - tt.quantity_sold,
            "sale_start": tt.sale_start,
            "sale_end": tt.sale_end,
            "is_active": tt.is_active,
        }
        for tt in ticket_types
    ]