"""
Payment processing service with Stripe integration
"""
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

import stripe
from stripe import StripeClient
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.payment import Payment, PaymentStatus, PaymentProvider, Refund, RefundStatus, PaymentWebhook, PaymentAttempt
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, RefundCreate, RefundUpdate,
    PaymentIntentCreate, PaymentIntentResponse, PaymentConfirmResponse
)

logger = logging.getLogger(__name__)


class StripeService:
    """Service for Stripe payment processing"""
    
    def __init__(self):
        """Initialize Stripe client with API key"""
        self.client = StripeClient(settings.STRIPE_SECRET_KEY)
        # Set webhook endpoint secret for verification
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    async def create_customer(self, user: User) -> Dict[str, Any]:
        """Create a Stripe customer for a user"""
        try:
            customer = self.client.customers.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else None,
                metadata={"user_id": user.id}
            )
            return customer
        except stripe.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create customer: {e.user_message}"
            )
    
    async def create_payment_intent(
        self, 
        amount: float, 
        currency: str = "USD",
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        receipt_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Stripe payment intent"""
        try:
            # Convert amount to cents for Stripe
            amount_cents = int(amount * 100)
            
            payment_intent_params = {
                "amount": amount_cents,
                "currency": currency.lower(),
                "automatic_payment_methods": {"enabled": True},
            }
            
            if customer_id:
                payment_intent_params["customer"] = customer_id
            if description:
                payment_intent_params["description"] = description
            if metadata:
                payment_intent_params["metadata"] = metadata
            if receipt_email:
                payment_intent_params["receipt_email"] = receipt_email
            
            payment_intent = self.client.payment_intents.create(**payment_intent_params)
            return payment_intent
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment intent: {e.user_message}"
            )
    
    async def confirm_payment_intent(
        self, 
        payment_intent_id: str,
        payment_method: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Confirm a payment intent"""
        try:
            confirm_params = {}
            if payment_method:
                confirm_params["payment_method"] = payment_method
            if return_url:
                confirm_params["return_url"] = return_url
            
            payment_intent = self.client.payment_intents.confirm(
                payment_intent_id, 
                **confirm_params
            )
            return payment_intent
            
        except stripe.StripeError as e:
            logger.error(f"Failed to confirm payment intent: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to confirm payment: {e.user_message}"
            )
    
    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Retrieve a payment intent from Stripe"""
        try:
            payment_intent = self.client.payment_intents.retrieve(payment_intent_id)
            return payment_intent
        except stripe.StripeError as e:
            logger.error(f"Failed to retrieve payment intent: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment intent not found: {e.user_message}"
            )
    
    async def create_refund(
        self, 
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a refund for a payment"""
        try:
            refund_params = {"payment_intent": payment_intent_id}
            
            if amount:
                # Convert amount to cents
                refund_params["amount"] = int(amount * 100)
            if reason:
                refund_params["reason"] = reason
            if metadata:
                refund_params["metadata"] = metadata
            
            refund = self.client.refunds.create(**refund_params)
            return refund
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create refund: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create refund: {e.user_message}"
            )
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Verify and parse a Stripe webhook"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )


class PaymentService:
    """Service for payment processing and database operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stripe = StripeService()
    
    async def create_payment_intent(
        self, 
        payment_data: PaymentIntentCreate,
        user: User
    ) -> PaymentIntentResponse:
        """Create payment intent and payment record"""
        
        # Get the order
        order = self.db.query(Order).filter(Order.id == payment_data.order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        if order.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to process payment for this order"
            )
        
        # Create Stripe customer if needed
        stripe_customer = await self.stripe.create_customer(user)
        
        # Create payment intent with Stripe
        stripe_payment_intent = await self.stripe.create_payment_intent(
            amount=payment_data.amount,
            currency=payment_data.currency,
            customer_id=stripe_customer.id,
            description=payment_data.description or f"Payment for order {order.id}",
            metadata={
                "order_id": order.id,
                "user_id": user.id,
                **(payment_data.metadata or {})
            },
            receipt_email=payment_data.receipt_email or user.email
        )
        
        # Create payment record in database
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order.id,
            user_id=user.id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            status=PaymentStatus.PENDING,
            provider=PaymentProvider.STRIPE,
            stripe_payment_intent_id=stripe_payment_intent.id,
            description=payment_data.description,
            receipt_email=payment_data.receipt_email or user.email,
            metadata=payment_data.metadata
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        return PaymentIntentResponse(
            id=payment.id,
            client_secret=stripe_payment_intent.client_secret,
            amount=payment_data.amount,
            currency=payment_data.currency,
            status=PaymentStatus.PENDING
        )
    
    async def confirm_payment(
        self, 
        payment_id: str,
        payment_method: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> PaymentConfirmResponse:
        """Confirm a payment intent"""
        
        # Get payment record
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        if not payment.stripe_payment_intent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe payment intent associated with this payment"
            )
        
        # Confirm with Stripe
        stripe_payment_intent = await self.stripe.confirm_payment_intent(
            payment.stripe_payment_intent_id,
            payment_method=payment_method,
            return_url=return_url
        )
        
        # Update payment status
        new_status = self._stripe_status_to_payment_status(stripe_payment_intent.status)
        payment.status = new_status
        
        if stripe_payment_intent.status == "succeeded":
            payment.processed_at = datetime.utcnow()
            # Update order status
            order = self.db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.status = OrderStatus.COMPLETED
                order.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        return PaymentConfirmResponse(
            payment_intent_id=payment.stripe_payment_intent_id,
            status=new_status,
            client_secret=stripe_payment_intent.client_secret if hasattr(stripe_payment_intent, 'client_secret') else None,
            next_action=stripe_payment_intent.next_action if hasattr(stripe_payment_intent, 'next_action') else None
        )
    
    async def create_refund(
        self, 
        refund_data: RefundCreate,
        user: User
    ) -> Refund:
        """Create a refund for a payment"""
        
        # Get payment record
        payment = self.db.query(Payment).filter(Payment.id == refund_data.payment_id).first()
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Verify user authorization (payment owner or admin)
        if payment.user_id != user.id:
            # TODO: Add admin role check
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to refund this payment"
            )
        
        if payment.status != PaymentStatus.SUCCEEDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only refund successful payments"
            )
        
        # Determine refund amount
        refund_amount = refund_data.amount or payment.amount
        
        # Create refund with Stripe
        stripe_refund = await self.stripe.create_refund(
            payment.stripe_payment_intent_id,
            amount=refund_amount,
            reason=refund_data.reason,
            metadata=refund_data.metadata
        )
        
        # Create refund record
        refund = Refund(
            id=str(uuid.uuid4()),
            payment_id=payment.id,
            order_id=payment.order_id,
            user_id=payment.user_id,
            amount=refund_amount,
            reason=refund_data.reason,
            status=RefundStatus.PENDING,
            stripe_refund_id=stripe_refund.id,
            description=refund_data.description,
            metadata=refund_data.metadata
        )
        
        self.db.add(refund)
        
        # Update payment status if full refund
        if refund_amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.db.commit()
        self.db.refresh(refund)
        
        return refund
    
    def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process a Stripe webhook event"""
        
        # Verify webhook signature
        event = self.stripe.verify_webhook_signature(payload, signature)
        
        # Store webhook event
        webhook = PaymentWebhook(
            id=str(uuid.uuid4()),
            provider=PaymentProvider.STRIPE,
            event_type=event["type"],
            event_id=event["id"],
            data=event["data"]
        )
        
        try:
            # Process the event
            if event["type"] == "payment_intent.succeeded":
                self._handle_payment_succeeded(event["data"]["object"])
            elif event["type"] == "payment_intent.payment_failed":
                self._handle_payment_failed(event["data"]["object"])
            elif event["type"] == "charge.dispute.created":
                self._handle_dispute_created(event["data"]["object"])
            # Add more event handlers as needed
            
            webhook.processed = True
            webhook.processed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to process webhook {event['id']}: {e}")
            webhook.processing_error = str(e)
        
        self.db.add(webhook)
        self.db.commit()
        
        return {"status": "success", "event_id": event["id"]}
    
    def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]):
        """Handle successful payment webhook"""
        payment = self.db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = PaymentStatus.SUCCEEDED
            payment.processed_at = datetime.utcnow()
            payment.stripe_charge_id = payment_intent.get("latest_charge")
            
            # Update order status
            order = self.db.query(Order).filter(Order.id == payment.order_id).first()
            if order:
                order.status = OrderStatus.COMPLETED
                order.completed_at = datetime.utcnow()
    
    def _handle_payment_failed(self, payment_intent: Dict[str, Any]):
        """Handle failed payment webhook"""
        payment = self.db.query(Payment).filter(
            Payment.stripe_payment_intent_id == payment_intent["id"]
        ).first()
        
        if payment:
            payment.status = PaymentStatus.FAILED
            if payment_intent.get("last_payment_error"):
                error = payment_intent["last_payment_error"]
                payment.failure_code = error.get("code")
                payment.failure_message = error.get("message")
    
    def _handle_dispute_created(self, charge: Dict[str, Any]):
        """Handle dispute creation webhook"""
        # Find payment by charge ID
        payment = self.db.query(Payment).filter(
            Payment.stripe_charge_id == charge["id"]
        ).first()
        
        if payment:
            # TODO: Implement dispute handling logic
            logger.warning(f"Dispute created for payment {payment.id}")
    
    def _stripe_status_to_payment_status(self, stripe_status: str) -> PaymentStatus:
        """Convert Stripe payment intent status to our PaymentStatus"""
        status_mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.REQUIRES_ACTION,
            "processing": PaymentStatus.PROCESSING,
            "requires_capture": PaymentStatus.PROCESSING,
            "canceled": PaymentStatus.CANCELLED,
            "succeeded": PaymentStatus.SUCCEEDED,
        }
        return status_mapping.get(stripe_status, PaymentStatus.PENDING) 