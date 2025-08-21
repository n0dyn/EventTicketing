from datetime import datetime
from typing import TYPE_CHECKING, List
import enum

from sqlalchemy import Column, DateTime, String, ForeignKey, Float, Integer, Boolean, Enum, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .event import Event  # noqa: F401


class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class TicketType(Base):
    """
    Database model for ticket types
    """
    __tablename__ = 'ticket_type'

    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("event.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    quantity_available = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean(), default=True)
    sale_start_date = Column(DateTime, nullable=True)
    sale_end_date = Column(DateTime, nullable=True)
    min_per_order = Column(Integer, default=1)
    max_per_order = Column(Integer, nullable=True)
    visibility = Column(Boolean(), default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="ticket_types")
    tickets = relationship("Ticket", back_populates="ticket_type", cascade="all, delete-orphan")
    price_tiers = relationship("PriceTier", back_populates="ticket_type", cascade="all, delete-orphan")
    promo_codes = relationship("PromoCode", secondary="promo_code_ticket_type", back_populates="ticket_types")


class PriceTier(Base):
    """
    Database model for ticket price tiers (early bird, regular, etc.)
    """
    __tablename__ = 'price_tier'

    id = Column(String, primary_key=True, index=True)
    ticket_type_id = Column(String, ForeignKey("ticket_type.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    quantity_available = Column(Integer, nullable=True)
    is_active = Column(Boolean(), default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticket_type = relationship("TicketType", back_populates="price_tiers")


class PromoCode(Base):
    """
    Database model for promotional codes
    """
    __tablename__ = 'promo_code'

    id = Column(String, primary_key=True, index=True)
    event_id = Column(String, ForeignKey("event.id"), nullable=False)
    code = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_type = Column(Enum(DiscountType), default=DiscountType.PERCENTAGE, nullable=False)
    discount_amount = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean(), default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    event = relationship("Event", backref="promo_codes")
    ticket_types = relationship("TicketType", secondary="promo_code_ticket_type", back_populates="promo_codes")

    # Add unique constraint for code within an event
    __table_args__ = (
        UniqueConstraint('event_id', 'code', name='uix_promo_code_event_code'),
    )


# Association table for PromoCode to TicketType many-to-many relationship
class PromoCodeTicketType(Base):
    """
    Association table for promo code to ticket type relationships
    """
    __tablename__ = 'promo_code_ticket_type'

    promo_code_id = Column(String, ForeignKey("promo_code.id"), primary_key=True)
    ticket_type_id = Column(String, ForeignKey("ticket_type.id"), primary_key=True)


class Ticket(Base):
    """
    Database model for individual tickets
    """
    __tablename__ = 'ticket'

    id = Column(String, primary_key=True, index=True)
    ticket_type_id = Column(String, ForeignKey("ticket_type.id"), nullable=False)
    order_id = Column(String, ForeignKey("order.id"), nullable=True)
    attendee_id = Column(String, ForeignKey("attendee.id"), nullable=True)
    code = Column(String, unique=True, nullable=False, index=True)  # QR code or unique identifier
    price_paid = Column(Float, nullable=False, default=0.0)
    promo_code_id = Column(String, ForeignKey("promo_code.id"), nullable=True)
    is_used = Column(Boolean(), default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ticket_type = relationship("TicketType", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")
    attendee = relationship("Attendee", back_populates="tickets")
    promo_code = relationship("PromoCode") 