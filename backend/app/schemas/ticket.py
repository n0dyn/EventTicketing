from typing import Optional, List, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, UUID4, Field, validator

from app.models.ticket import DiscountType


# TicketType schemas
class TicketTypeBase(BaseModel):
    """
    Base TicketType schema with shared properties
    """
    name: str
    description: Optional[str] = None
    price: float = 0.0
    quantity_available: int = 0
    is_active: bool = True
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None
    min_per_order: int = 1
    max_per_order: Optional[int] = None
    visibility: bool = True
    sort_order: int = 0


class TicketTypeCreate(TicketTypeBase):
    """
    TicketType creation schema
    """
    pass


class TicketTypeUpdate(TicketTypeBase):
    """
    TicketType update schema
    """
    name: Optional[str] = None
    price: Optional[float] = None
    quantity_available: Optional[int] = None
    is_active: Optional[bool] = None


class TicketTypeInDBBase(TicketTypeBase):
    """
    Base schema for TicketType in DB
    """
    id: UUID4
    event_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TicketType(TicketTypeInDBBase):
    """
    TicketType schema for response
    """
    price_tiers: List["PriceTier"] = []


# PriceTier schemas
class PriceTierBase(BaseModel):
    """
    Base PriceTier schema with shared properties
    """
    name: str
    price: float
    start_date: datetime
    end_date: datetime
    quantity_available: Optional[int] = None
    is_active: bool = True


class PriceTierCreate(PriceTierBase):
    """
    PriceTier creation schema
    """
    pass


class PriceTierUpdate(PriceTierBase):
    """
    PriceTier update schema
    """
    name: Optional[str] = None
    price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class PriceTierInDBBase(PriceTierBase):
    """
    Base schema for PriceTier in DB
    """
    id: UUID4
    ticket_type_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PriceTier(PriceTierInDBBase):
    """
    PriceTier schema for response
    """
    pass


# PromoCode schemas
class PromoCodeBase(BaseModel):
    """
    Base PromoCode schema with shared properties
    """
    code: str
    description: Optional[str] = None
    discount_type: DiscountType = DiscountType.PERCENTAGE
    discount_amount: float = Field(..., ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    is_active: bool = True
    
    @validator('discount_amount')
    def validate_discount_amount(cls, v, values):
        if 'discount_type' in values and values['discount_type'] == DiscountType.PERCENTAGE and v > 100:
            raise ValueError('Percentage discount cannot exceed 100%')
        return v


class PromoCodeCreate(PromoCodeBase):
    """
    PromoCode creation schema
    """
    ticket_type_ids: Optional[List[UUID4]] = None


class PromoCodeUpdate(PromoCodeBase):
    """
    PromoCode update schema
    """
    code: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_amount: Optional[float] = None
    is_active: Optional[bool] = None
    ticket_type_ids: Optional[List[UUID4]] = None


class PromoCodeInDBBase(PromoCodeBase):
    """
    Base schema for PromoCode in DB
    """
    id: UUID4
    event_id: UUID4
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PromoCode(PromoCodeInDBBase):
    """
    PromoCode schema for response
    """
    ticket_types: List[TicketType] = []


class PromoCodeValidation(BaseModel):
    """
    Schema for validating a promo code
    """
    code: str
    event_id: UUID4


class PromoCodeValidationResponse(BaseModel):
    """
    Schema for promo code validation response
    """
    is_valid: bool
    promo_code: Optional[PromoCode] = None
    message: Optional[str] = None


# Ticket schemas
class TicketBase(BaseModel):
    """
    Base Ticket schema with shared properties
    """
    code: str
    price_paid: float = 0.0
    is_used: bool = False
    used_at: Optional[datetime] = None


class TicketCreate(TicketBase):
    """
    Ticket creation schema
    """
    promo_code_id: Optional[UUID4] = None


class TicketUpdate(TicketBase):
    """
    Ticket update schema
    """
    code: Optional[str] = None
    is_used: Optional[bool] = None
    used_at: Optional[datetime] = None


class TicketInDBBase(TicketBase):
    """
    Base schema for Ticket in DB
    """
    id: UUID4
    ticket_type_id: UUID4
    order_id: Optional[UUID4] = None
    attendee_id: Optional[UUID4] = None
    promo_code_id: Optional[UUID4] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class Ticket(TicketInDBBase):
    """
    Ticket schema for response
    """
    ticket_type: Optional[TicketType] = None
    promo_code: Optional[PromoCode] = None


# To avoid circular import issues
TicketType.update_forward_refs() 