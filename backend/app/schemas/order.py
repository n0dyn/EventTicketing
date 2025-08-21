from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod


# Cart Item Schemas
class CartItemBase(BaseModel):
    ticket_type_id: str
    quantity: int = Field(1, gt=0)


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)


class CartItemInDB(CartItemBase):
    id: str
    cart_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# Cart Schemas
class CartBase(BaseModel):
    pass


class CartCreate(CartBase):
    pass


class CartUpdate(CartBase):
    pass


class CartInDB(CartBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    items: List[CartItemInDB] = []

    class Config:
        orm_mode = True


# Order Schemas
class OrderBase(BaseModel):
    user_id: str
    total_amount: float = 0.0


class OrderCreate(OrderBase):
    payment_method: Optional[PaymentMethod] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_method: Optional[PaymentMethod] = None
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None


class OrderInDB(OrderBase):
    id: str
    status: OrderStatus
    payment_method: Optional[PaymentMethod] = None
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_country: Optional[str] = None
    billing_postal_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# Public schemas
class CartItem(CartItemInDB):
    pass


class Cart(CartInDB):
    pass


class Order(OrderInDB):
    pass 