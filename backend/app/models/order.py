from datetime import datetime
from typing import TYPE_CHECKING, List
from enum import Enum

from sqlalchemy import Column, DateTime, String, ForeignKey, Float, Integer, Boolean, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .user import User  # noqa: F401
    from .ticket import Ticket  # noqa: F401


class OrderStatus(str, Enum):
    """Enum for order status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Enum for payment methods"""
    CREDIT_CARD = "credit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class Order(Base):
    """
    Database model for orders
    """
    __tablename__ = 'order'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    event_id = Column(String, ForeignKey("event.id"), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(SQLAlchemyEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    payment_method = Column(SQLAlchemyEnum(PaymentMethod), nullable=True)
    payment_id = Column(String, nullable=True)  # External payment system reference
    transaction_id = Column(String, nullable=True, unique=True)  # Unique transaction identifier
    billing_address = Column(String, nullable=True)
    billing_city = Column(String, nullable=True)
    billing_country = Column(String, nullable=True)
    billing_postal_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="orders")
    tickets = relationship("Ticket", back_populates="order")
    cart_items = relationship("CartItem", back_populates="order", cascade="all, delete-orphan")


class Cart(Base):
    """
    Database model for shopping cart
    """
    __tablename__ = 'cart'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user.id"), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Cart expiration time

    # Relationships
    user = relationship("User", backref="cart", uselist=False)
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    """
    Database model for shopping cart items
    """
    __tablename__ = 'cart_item'

    id = Column(String, primary_key=True, index=True)
    cart_id = Column(String, ForeignKey("cart.id"), nullable=False)
    ticket_type_id = Column(String, ForeignKey("ticket_type.id"), nullable=False)
    order_id = Column(String, ForeignKey("order.id"), nullable=True)  # Set when converted to order
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cart = relationship("Cart", back_populates="items")
    ticket_type = relationship("TicketType")
    order = relationship("Order", back_populates="cart_items") 