from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.api import deps
from app.services.ticket import ticket_type_service, ticket_service, price_tier_service, promo_code_service

router = APIRouter()


@router.post("/events/{event_id}/ticket-types", response_model=schemas.TicketType)
async def create_ticket_type(
    event_id: str,
    ticket_type_in: schemas.TicketTypeCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new ticket type for an event.
    """
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create ticket types for this event",
        )
    ticket_type = await ticket_type_service.create(db=db, obj_in=ticket_type_in, event_id=event_id)
    return ticket_type


@router.get("/events/{event_id}/ticket-types", response_model=List[schemas.TicketType])
async def read_ticket_types(
    event_id: str,
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = Query(False, description="Return only active tickets"),
) -> Any:
    """
    Get ticket types for an event.
    """
    if active_only:
        ticket_types = await ticket_type_service.get_active_by_event(
            db=db, event_id=event_id, skip=skip, limit=limit
        )
    else:
        ticket_types = await ticket_type_service.get_multi_by_event(
            db=db, event_id=event_id, skip=skip, limit=limit
        )
    return ticket_types


@router.get("/ticket-types/{id}", response_model=schemas.TicketType)
async def read_ticket_type(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get ticket type by ID.
    """
    ticket_type = await ticket_type_service.get(db=db, id=id)
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found",
        )
    return ticket_type


@router.put("/ticket-types/{id}", response_model=schemas.TicketType)
async def update_ticket_type(
    id: str,
    ticket_type_in: schemas.TicketTypeUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a ticket type.
    """
    ticket_type = await ticket_type_service.get(db=db, id=id)
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found",
        )
    event = await db.get(models.Event, ticket_type.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this ticket type",
        )
    ticket_type = await ticket_type_service.update(db=db, db_obj=ticket_type, obj_in=ticket_type_in)
    return ticket_type


@router.delete("/ticket-types/{id}", response_model=schemas.TicketType)
async def delete_ticket_type(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a ticket type.
    """
    ticket_type = await ticket_type_service.get(db=db, id=id)
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found",
        )
    event = await db.get(models.Event, ticket_type.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this ticket type",
        )
    ticket_type = await ticket_type_service.remove(db=db, id=id)
    return ticket_type


@router.post("/ticket-types/{ticket_type_id}/price-tiers", response_model=schemas.PriceTier)
async def create_price_tier(
    ticket_type_id: str,
    price_tier_in: schemas.PriceTierCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new price tier for a ticket type.
    """
    ticket_type = await ticket_type_service.get(db=db, id=ticket_type_id)
    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket type not found",
        )
    
    event = await db.get(models.Event, ticket_type.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create price tiers for this ticket type",
        )
    
    price_tier = await price_tier_service.create(
        db=db, obj_in=price_tier_in, ticket_type_id=ticket_type_id
    )
    return price_tier


@router.get("/ticket-types/{ticket_type_id}/price-tiers", response_model=List[schemas.PriceTier])
async def read_price_tiers(
    ticket_type_id: str,
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get price tiers for a ticket type.
    """
    price_tiers = await price_tier_service.get_multi_by_ticket_type(
        db=db, ticket_type_id=ticket_type_id, skip=skip, limit=limit
    )
    return price_tiers


@router.get("/price-tiers/{id}", response_model=schemas.PriceTier)
async def read_price_tier(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Get price tier by ID.
    """
    price_tier = await price_tier_service.get(db=db, id=id)
    if not price_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price tier not found",
        )
    return price_tier


@router.put("/price-tiers/{id}", response_model=schemas.PriceTier)
async def update_price_tier(
    id: str,
    price_tier_in: schemas.PriceTierUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a price tier.
    """
    price_tier = await price_tier_service.get(db=db, id=id)
    if not price_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price tier not found",
        )
    
    ticket_type = await ticket_type_service.get(db=db, id=price_tier.ticket_type_id)
    event = await db.get(models.Event, ticket_type.event_id)
    
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this price tier",
        )
    
    price_tier = await price_tier_service.update(db=db, db_obj=price_tier, obj_in=price_tier_in)
    return price_tier


@router.delete("/price-tiers/{id}", response_model=schemas.PriceTier)
async def delete_price_tier(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a price tier.
    """
    price_tier = await price_tier_service.get(db=db, id=id)
    if not price_tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Price tier not found",
        )
    
    ticket_type = await ticket_type_service.get(db=db, id=price_tier.ticket_type_id)
    event = await db.get(models.Event, ticket_type.event_id)
    
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this price tier",
        )
    
    price_tier = await price_tier_service.remove(db=db, id=id)
    return price_tier


@router.post("/events/{event_id}/promo-codes", response_model=schemas.PromoCode)
async def create_promo_code(
    event_id: str,
    promo_code_in: schemas.PromoCodeCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new promo code for an event.
    """
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create promo codes for this event",
        )
    
    # Check if the provided ticket types belong to this event
    if promo_code_in.ticket_type_ids:
        for ticket_type_id in promo_code_in.ticket_type_ids:
            ticket_type = await ticket_type_service.get(db=db, id=str(ticket_type_id))
            if not ticket_type or ticket_type.event_id != event_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ticket type with ID {ticket_type_id} does not belong to this event",
                )
    
    # Check if code already exists for this event
    existing_code = await promo_code_service.get_by_code(db=db, event_id=event_id, code=promo_code_in.code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A promo code with this code already exists for this event",
        )
    
    promo_code = await promo_code_service.create(db=db, obj_in=promo_code_in, event_id=event_id)
    return promo_code


@router.get("/events/{event_id}/promo-codes", response_model=List[schemas.PromoCode])
async def read_promo_codes(
    event_id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get promo codes for an event.
    """
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view promo codes for this event",
        )
    
    promo_codes = await promo_code_service.get_multi_by_event(
        db=db, event_id=event_id, skip=skip, limit=limit
    )
    return promo_codes


@router.get("/promo-codes/{id}", response_model=schemas.PromoCode)
async def read_promo_code(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get promo code by ID.
    """
    promo_code = await promo_code_service.get(db=db, id=id)
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found",
        )
    
    event = await db.get(models.Event, promo_code.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this promo code",
        )
    
    return promo_code


@router.put("/promo-codes/{id}", response_model=schemas.PromoCode)
async def update_promo_code(
    id: str,
    promo_code_in: schemas.PromoCodeUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a promo code.
    """
    promo_code = await promo_code_service.get(db=db, id=id)
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found",
        )
    
    event = await db.get(models.Event, promo_code.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this promo code",
        )
    
    # Check if code is being changed and if it already exists
    if promo_code_in.code and promo_code_in.code != promo_code.code:
        existing_code = await promo_code_service.get_by_code(
            db=db, event_id=promo_code.event_id, code=promo_code_in.code
        )
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A promo code with this code already exists for this event",
            )
    
    # Check if the provided ticket types belong to this event
    if promo_code_in.ticket_type_ids:
        for ticket_type_id in promo_code_in.ticket_type_ids:
            ticket_type = await ticket_type_service.get(db=db, id=str(ticket_type_id))
            if not ticket_type or ticket_type.event_id != promo_code.event_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ticket type with ID {ticket_type_id} does not belong to this event",
                )
    
    promo_code = await promo_code_service.update(db=db, db_obj=promo_code, obj_in=promo_code_in)
    return promo_code


@router.delete("/promo-codes/{id}", response_model=schemas.PromoCode)
async def delete_promo_code(
    id: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a promo code.
    """
    promo_code = await promo_code_service.get(db=db, id=id)
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found",
        )
    
    event = await db.get(models.Event, promo_code.event_id)
    if not current_user.is_superuser and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this promo code",
        )
    
    promo_code = await promo_code_service.remove(db=db, id=id)
    return promo_code


@router.post("/events/{event_id}/validate-promo-code", response_model=schemas.PromoCodeValidationResponse)
async def validate_promo_code(
    event_id: str,
    validation: schemas.PromoCodeValidation,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Validate a promo code for an event.
    """
    # Check if the event exists
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    # Validate the promo code
    validation_result = await promo_code_service.validate_promo_code(
        db=db, event_id=event_id, code=validation.code
    )
    
    return validation_result 