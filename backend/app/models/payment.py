from datetime import datetime
from typing import TYPE_CHECKING, Optional
from enum import Enum

from sqlalchemy import Column, DateTime, String, ForeignKey, Float, Integer, Boolean, Enum as SQLAlchemyEnum, Text, JSON
from sqlalchemy.orm import relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from .order import Order  # noqa: F401
    from .user import User  # noqa: F401


class PaymentStatus(str, Enum):
    """Enum for payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_ACTION = "requires_action"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


class PaymentProvider(str, Enum):
    """Enum for payment providers"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    MANUAL = "manual"


class RefundStatus(str, Enum):
    """Enum for refund status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Payment(Base):
    """
    Database model for payments
    """
    __tablename__ = 'payment'

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("order.id"), nullable=False)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(SQLAlchemyEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    provider = Column(SQLAlchemyEnum(PaymentProvider), nullable=False, default=PaymentProvider.STRIPE)
    
    # Provider-specific IDs
    stripe_payment_intent_id = Column(String, nullable=True, unique=True)
    stripe_charge_id = Column(String, nullable=True)
    provider_payment_id = Column(String, nullable=True)  # Generic provider reference
    
    # Payment metadata
    payment_method_type = Column(String, nullable=True)  # card, bank_transfer, etc.
    description = Column(String, nullable=True)
    receipt_email = Column(String, nullable=True)
    
    # Failure information
    failure_code = Column(String, nullable=True)
    failure_message = Column(String, nullable=True)
    
    # Metadata and logs
    payment_metadata = Column(JSON, nullable=True)  # Store additional payment data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    order = relationship("Order", backref="payments")
    user = relationship("User", backref="payments")
    refunds = relationship("Refund", back_populates="payment")


class Refund(Base):
    """
    Database model for refunds
    """
    __tablename__ = 'refund'

    id = Column(String, primary_key=True, index=True)
    payment_id = Column(String, ForeignKey("payment.id"), nullable=False)
    order_id = Column(String, ForeignKey("order.id"), nullable=False)
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    
    # Refund details
    amount = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(RefundStatus), nullable=False, default=RefundStatus.PENDING)
    
    # Provider-specific IDs
    stripe_refund_id = Column(String, nullable=True, unique=True)
    provider_refund_id = Column(String, nullable=True)
    
    # Refund metadata
    description = Column(Text, nullable=True)
    refund_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    payment = relationship("Payment", back_populates="refunds")
    order = relationship("Order", backref="refunds")
    user = relationship("User", backref="refunds")


class PaymentWebhook(Base):
    """
    Database model for tracking payment webhook events
    """
    __tablename__ = 'payment_webhook'

    id = Column(String, primary_key=True, index=True)
    provider = Column(SQLAlchemyEnum(PaymentProvider), nullable=False)
    event_type = Column(String, nullable=False)
    event_id = Column(String, nullable=False, unique=True)  # Provider's event ID
    
    # Webhook data
    data = Column(JSON, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Related entities
    payment_id = Column(String, ForeignKey("payment.id"), nullable=True)
    order_id = Column(String, ForeignKey("order.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    payment = relationship("Payment", backref="webhooks")
    order = relationship("Order", backref="payment_webhooks")


class PaymentAttempt(Base):
    """
    Database model for tracking payment attempts and failures
    """
    __tablename__ = 'payment_attempt'

    id = Column(String, primary_key=True, index=True)
    payment_id = Column(String, ForeignKey("payment.id"), nullable=False)
    order_id = Column(String, ForeignKey("order.id"), nullable=False)
    
    # Attempt details
    amount = Column(Float, nullable=False)
    status = Column(SQLAlchemyEnum(PaymentStatus), nullable=False)
    provider_attempt_id = Column(String, nullable=True)
    
    # Error information
    error_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    error_type = Column(String, nullable=True)  # card_error, api_error, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    payment = relationship("Payment", backref="attempts")
    order = relationship("Order", backref="payment_attempts") 