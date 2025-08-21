from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, validator

from app.models.payment import PaymentStatus, PaymentProvider, RefundStatus


# Payment Intent Creation
class PaymentIntentCreate(BaseModel):
    """Schema for creating a payment intent"""
    order_id: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    receipt_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response"""
    id: str
    client_secret: str
    amount: float
    currency: str
    status: PaymentStatus
    
    model_config = ConfigDict(from_attributes=True)


# Payment Processing
class PaymentCreate(BaseModel):
    """Schema for creating a payment record"""
    order_id: str
    amount: float
    currency: str = "USD"
    provider: PaymentProvider = PaymentProvider.STRIPE
    stripe_payment_intent_id: Optional[str] = None
    payment_method_type: Optional[str] = None
    description: Optional[str] = None
    receipt_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PaymentUpdate(BaseModel):
    """Schema for updating a payment record"""
    status: Optional[PaymentStatus] = None
    stripe_charge_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    payment_method_type: Optional[str] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class Payment(BaseModel):
    """Schema for payment response"""
    id: str
    order_id: str
    user_id: str
    amount: float
    currency: str
    status: PaymentStatus
    provider: PaymentProvider
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    payment_method_type: Optional[str] = None
    description: Optional[str] = None
    receipt_email: Optional[str] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Refund Processing
class RefundCreate(BaseModel):
    """Schema for creating a refund"""
    payment_id: str
    amount: Optional[float] = None  # If None, refund full amount
    reason: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RefundUpdate(BaseModel):
    """Schema for updating a refund"""
    status: Optional[RefundStatus] = None
    stripe_refund_id: Optional[str] = None
    provider_refund_id: Optional[str] = None
    processed_at: Optional[datetime] = None


class Refund(BaseModel):
    """Schema for refund response"""
    id: str
    payment_id: str
    order_id: str
    user_id: str
    amount: float
    reason: Optional[str] = None
    status: RefundStatus
    stripe_refund_id: Optional[str] = None
    provider_refund_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Webhook Processing
class WebhookEvent(BaseModel):
    """Schema for processing webhook events"""
    event_type: str
    event_id: str
    data: Dict[str, Any]
    provider: PaymentProvider = PaymentProvider.STRIPE


class PaymentWebhook(BaseModel):
    """Schema for payment webhook response"""
    id: str
    provider: PaymentProvider
    event_type: str
    event_id: str
    data: Dict[str, Any]
    processed: bool
    processing_error: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# Payment Methods
class PaymentMethodCreate(BaseModel):
    """Schema for creating a payment method"""
    type: str  # card, bank_account, etc.
    card: Optional[Dict[str, Any]] = None
    billing_details: Optional[Dict[str, Any]] = None


class PaymentMethodResponse(BaseModel):
    """Schema for payment method response"""
    id: str
    type: str
    card: Optional[Dict[str, Any]] = None
    billing_details: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


# Customer Management
class CustomerCreate(BaseModel):
    """Schema for creating a Stripe customer"""
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CustomerResponse(BaseModel):
    """Schema for customer response"""
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


# Payment Confirmation
class PaymentConfirm(BaseModel):
    """Schema for confirming a payment"""
    payment_intent_id: str
    payment_method: Optional[str] = None
    return_url: Optional[str] = None


class PaymentConfirmResponse(BaseModel):
    """Schema for payment confirmation response"""
    payment_intent_id: str
    status: PaymentStatus
    client_secret: Optional[str] = None
    next_action: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(from_attributes=True)


# Lists and Pagination
class PaymentList(BaseModel):
    """Schema for paginated payment list"""
    payments: List[Payment]
    total: int
    page: int
    per_page: int
    pages: int


class RefundList(BaseModel):
    """Schema for paginated refund list"""
    refunds: List[Refund]
    total: int
    page: int
    per_page: int
    pages: int


# Error Responses
class PaymentError(BaseModel):
    """Schema for payment error responses"""
    error_type: str
    error_code: Optional[str] = None
    error_message: str
    details: Optional[Dict[str, Any]] = None 