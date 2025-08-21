from typing import Any, Dict, Optional, List, Union
from datetime import datetime

from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crud_base import CRUDBase
from app.models.ticket import TicketType, Ticket, PriceTier, PromoCode, PromoCodeTicketType
from app.schemas.ticket import (
    TicketTypeCreate, TicketTypeUpdate, 
    TicketCreate, TicketUpdate,
    PriceTierCreate, PriceTierUpdate,
    PromoCodeCreate, PromoCodeUpdate
)


class CRUDTicketType(CRUDBase[TicketType, TicketTypeCreate, TicketTypeUpdate]):
    async def get(self, db: AsyncSession, id: str) -> Optional[TicketType]:
        """
        Get a ticket type by ID
        """
        result = await db.execute(
            select(TicketType)
            .options(selectinload(TicketType.price_tiers))
            .where(TicketType.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi_by_event(
        self, db: AsyncSession, *, event_id: str, skip: int = 0, limit: int = 100
    ) -> List[TicketType]:
        """
        Get multiple ticket types by event ID
        """
        result = await db.execute(
            select(TicketType)
            .options(selectinload(TicketType.price_tiers))
            .where(TicketType.event_id == event_id)
            .order_by(TicketType.sort_order, TicketType.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_by_event(
        self, db: AsyncSession, *, event_id: str, skip: int = 0, limit: int = 100
    ) -> List[TicketType]:
        """
        Get active ticket types for an event (considering sale dates and is_active)
        """
        now = datetime.utcnow()
        result = await db.execute(
            select(TicketType)
            .options(selectinload(TicketType.price_tiers))
            .where(
                TicketType.event_id == event_id,
                TicketType.is_active == True,
                (TicketType.sale_start_date.is_(None) | (TicketType.sale_start_date <= now)),
                (TicketType.sale_end_date.is_(None) | (TicketType.sale_end_date >= now))
            )
            .order_by(TicketType.sort_order, TicketType.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: TicketTypeCreate, event_id: str) -> TicketType:
        """
        Create a new ticket type
        """
        db_obj = TicketType(
            **obj_in.dict(exclude_unset=True),
            event_id=event_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: TicketType, obj_in: Union[TicketTypeUpdate, Dict[str, Any]]
    ) -> TicketType:
        """
        Update a ticket type
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def remove(self, db: AsyncSession, *, id: str) -> TicketType:
        """
        Delete a ticket type
        """
        obj = await db.get(TicketType, id)
        if not obj:
            raise ValueError(f"TicketType with ID {id} not found")
        await db.delete(obj)
        await db.commit()
        return obj


class CRUDPriceTier(CRUDBase[PriceTier, PriceTierCreate, PriceTierUpdate]):
    async def get(self, db: AsyncSession, id: str) -> Optional[PriceTier]:
        """
        Get a price tier by ID
        """
        result = await db.execute(select(PriceTier).where(PriceTier.id == id))
        return result.scalar_one_or_none()

    async def get_multi_by_ticket_type(
        self, db: AsyncSession, *, ticket_type_id: str, skip: int = 0, limit: int = 100
    ) -> List[PriceTier]:
        """
        Get multiple price tiers by ticket type ID
        """
        result = await db.execute(
            select(PriceTier)
            .where(PriceTier.ticket_type_id == ticket_type_id)
            .order_by(PriceTier.start_date)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_price_tier(
        self, db: AsyncSession, *, ticket_type_id: str
    ) -> Optional[PriceTier]:
        """
        Get the currently active price tier for a ticket type
        """
        now = datetime.utcnow()
        result = await db.execute(
            select(PriceTier)
            .where(
                PriceTier.ticket_type_id == ticket_type_id,
                PriceTier.is_active == True,
                PriceTier.start_date <= now,
                PriceTier.end_date >= now
            )
            .order_by(PriceTier.start_date.desc())
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: PriceTierCreate, ticket_type_id: str) -> PriceTier:
        """
        Create a new price tier
        """
        db_obj = PriceTier(
            **obj_in.dict(exclude_unset=True),
            ticket_type_id=ticket_type_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: PriceTier, obj_in: Union[PriceTierUpdate, Dict[str, Any]]
    ) -> PriceTier:
        """
        Update a price tier
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def remove(self, db: AsyncSession, *, id: str) -> PriceTier:
        """
        Delete a price tier
        """
        obj = await db.get(PriceTier, id)
        if not obj:
            raise ValueError(f"PriceTier with ID {id} not found")
        await db.delete(obj)
        await db.commit()
        return obj


class CRUDPromoCode(CRUDBase[PromoCode, PromoCodeCreate, PromoCodeUpdate]):
    async def get(self, db: AsyncSession, id: str) -> Optional[PromoCode]:
        """
        Get a promo code by ID
        """
        result = await db.execute(
            select(PromoCode)
            .options(selectinload(PromoCode.ticket_types))
            .where(PromoCode.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, *, event_id: str, code: str) -> Optional[PromoCode]:
        """
        Get a promo code by its code string for a specific event
        """
        result = await db.execute(
            select(PromoCode)
            .options(selectinload(PromoCode.ticket_types))
            .where(
                PromoCode.event_id == event_id,
                PromoCode.code == code
            )
        )
        return result.scalar_one_or_none()

    async def get_multi_by_event(
        self, db: AsyncSession, *, event_id: str, skip: int = 0, limit: int = 100
    ) -> List[PromoCode]:
        """
        Get multiple promo codes by event ID
        """
        result = await db.execute(
            select(PromoCode)
            .options(selectinload(PromoCode.ticket_types))
            .where(PromoCode.event_id == event_id)
            .order_by(PromoCode.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: PromoCodeCreate, event_id: str) -> PromoCode:
        """
        Create a new promo code
        """
        # Create promo code without ticket_type_ids
        obj_data = obj_in.dict(exclude={"ticket_type_ids"})
        db_obj = PromoCode(
            **obj_data,
            event_id=event_id
        )
        db.add(db_obj)
        await db.flush()  # Flush to get the ID but don't commit yet
        
        # Add ticket type associations if provided
        if obj_in.ticket_type_ids:
            for ticket_type_id in obj_in.ticket_type_ids:
                association = PromoCodeTicketType(
                    promo_code_id=db_obj.id,
                    ticket_type_id=ticket_type_id
                )
                db.add(association)
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: PromoCode, obj_in: Union[PromoCodeUpdate, Dict[str, Any]]
    ) -> PromoCode:
        """
        Update a promo code
        """
        ticket_type_ids = None
        if isinstance(obj_in, dict):
            update_data = obj_in.copy()
            ticket_type_ids = update_data.pop("ticket_type_ids", None)
        else:
            update_data = obj_in.dict(exclude={"ticket_type_ids"}, exclude_unset=True)
            ticket_type_ids = obj_in.ticket_type_ids if hasattr(obj_in, "ticket_type_ids") else None
        
        # Update the promo code
        updated_obj = await super().update(db, db_obj=db_obj, obj_in=update_data)
        
        # Update ticket type associations if provided
        if ticket_type_ids is not None:
            # Remove existing associations
            await db.execute(
                update(PromoCodeTicketType)
                .where(PromoCodeTicketType.promo_code_id == db_obj.id)
                .values({"promo_code_id": None})
            )
            await db.flush()
            
            # Add new associations
            for ticket_type_id in ticket_type_ids:
                association = PromoCodeTicketType(
                    promo_code_id=db_obj.id,
                    ticket_type_id=ticket_type_id
                )
                db.add(association)
        
        await db.commit()
        await db.refresh(updated_obj)
        return updated_obj

    async def remove(self, db: AsyncSession, *, id: str) -> PromoCode:
        """
        Delete a promo code
        """
        obj = await db.get(PromoCode, id)
        if not obj:
            raise ValueError(f"PromoCode with ID {id} not found")
        await db.delete(obj)
        await db.commit()
        return obj

    async def validate_promo_code(
        self, db: AsyncSession, *, event_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Validate if a promo code is valid for use
        """
        promo_code = await self.get_by_code(db, event_id=event_id, code=code)
        
        # Check if promo code exists
        if not promo_code:
            return {
                "is_valid": False,
                "message": "Promo code does not exist"
            }
        
        # Check if promo code is active
        if not promo_code.is_active:
            return {
                "is_valid": False,
                "message": "Promo code is not active"
            }
        
        # Check date validity
        now = datetime.utcnow()
        if promo_code.start_date and promo_code.start_date > now:
            return {
                "is_valid": False,
                "message": "Promo code is not yet valid"
            }
        
        if promo_code.end_date and promo_code.end_date < now:
            return {
                "is_valid": False,
                "message": "Promo code has expired"
            }
        
        # Check usage limit
        if promo_code.usage_limit and promo_code.usage_count >= promo_code.usage_limit:
            return {
                "is_valid": False,
                "message": "Promo code usage limit reached"
            }
        
        # If all checks pass, the promo code is valid
        return {
            "is_valid": True,
            "promo_code": promo_code,
            "message": "Promo code is valid"
        }

    async def increment_usage_count(self, db: AsyncSession, *, promo_code_id: str) -> PromoCode:
        """
        Increment the usage count of a promo code
        """
        promo_code = await self.get(db, id=promo_code_id)
        if not promo_code:
            raise ValueError(f"PromoCode with ID {promo_code_id} not found")
        
        promo_code.usage_count += 1
        db.add(promo_code)
        await db.commit()
        await db.refresh(promo_code)
        return promo_code


class CRUDTicket(CRUDBase[Ticket, TicketCreate, TicketUpdate]):
    async def get(self, db: AsyncSession, id: str) -> Optional[Ticket]:
        """
        Get a ticket by ID
        """
        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.promo_code)
            )
            .where(Ticket.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Ticket]:
        """
        Get a ticket by code
        """
        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.promo_code)
            )
            .where(Ticket.code == code)
        )
        return result.scalar_one_or_none()

    async def get_multi_by_ticket_type(
        self, db: AsyncSession, *, ticket_type_id: str, skip: int = 0, limit: int = 100
    ) -> List[Ticket]:
        """
        Get multiple tickets by ticket type ID
        """
        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.promo_code)
            )
            .where(Ticket.ticket_type_id == ticket_type_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_multi_by_order(
        self, db: AsyncSession, *, order_id: str, skip: int = 0, limit: int = 100
    ) -> List[Ticket]:
        """
        Get multiple tickets by order ID
        """
        result = await db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.ticket_type),
                selectinload(Ticket.promo_code)
            )
            .where(Ticket.order_id == order_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, obj_in: TicketCreate, ticket_type_id: str, order_id: Optional[str] = None
    ) -> Ticket:
        """
        Create a new ticket
        """
        db_obj = Ticket(
            **obj_in.dict(exclude_unset=True),
            ticket_type_id=ticket_type_id,
            order_id=order_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: Ticket, obj_in: Union[TicketUpdate, Dict[str, Any]]
    ) -> Ticket:
        """
        Update a ticket
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def remove(self, db: AsyncSession, *, id: str) -> Ticket:
        """
        Delete a ticket
        """
        obj = await db.get(Ticket, id)
        if not obj:
            raise ValueError(f"Ticket with ID {id} not found")
        await db.delete(obj)
        await db.commit()
        return obj

    async def mark_as_used(self, db: AsyncSession, *, db_obj: Ticket) -> Ticket:
        """
        Mark a ticket as used
        """
        db_obj.is_used = True
        db_obj.used_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def assign_to_attendee(self, db: AsyncSession, *, ticket_id: str, attendee_id: str) -> Ticket:
        """
        Assign a ticket to an attendee
        """
        ticket = await self.get(db, id=ticket_id)
        if not ticket:
            raise ValueError(f"Ticket with ID {ticket_id} not found")
        
        ticket.attendee_id = attendee_id
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        return ticket


ticket_type_service = CRUDTicketType(TicketType)
price_tier_service = CRUDPriceTier(PriceTier)
promo_code_service = CRUDPromoCode(PromoCode)
ticket_service = CRUDTicket(Ticket) 