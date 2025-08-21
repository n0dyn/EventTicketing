"""
Payment processing API endpoints
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.models.payment import Payment, Refund
from app.schemas.payment import (
    PaymentIntentCreate, PaymentIntentResponse, 
    PaymentConfirm, PaymentConfirmResponse,
    Payment as PaymentSchema, PaymentList,
    RefundCreate, Refund as RefundSchema, RefundList,
    PaymentError
)
from app.services.payment import PaymentService

router = APIRouter()


@router.post("/payment-intents", response_model=PaymentIntentResponse)
async def create_payment_intent(
    *,
    db: Session = Depends(get_db),
    payment_data: PaymentIntentCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create a payment intent for an order
    """
    try:
        payment_service = PaymentService(db)
        payment_intent = await payment_service.create_payment_intent(
            payment_data=payment_data,
            user=current_user
        )
        return payment_intent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )


@router.post("/payments/{payment_id}/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    *,
    db: Session = Depends(get_db),
    payment_id: str,
    payment_confirm: PaymentConfirm,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Confirm a payment intent
    """
    try:
        payment_service = PaymentService(db)
        confirmation = await payment_service.confirm_payment(
            payment_id=payment_id,
            payment_method=payment_confirm.payment_method,
            return_url=payment_confirm.return_url
        )
        return confirmation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}"
        )


@router.get("/payments", response_model=PaymentList)
def get_payments(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get user's payment history
    """
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    total = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).count()
    
    return PaymentList(
        payments=payments,
        total=total,
        page=skip // limit + 1,
        per_page=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/payments/{payment_id}", response_model=PaymentSchema)
def get_payment(
    *,
    db: Session = Depends(get_db),
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get a specific payment by ID
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    if payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return payment


@router.post("/payments/{payment_id}/refund", response_model=RefundSchema)
async def create_refund(
    *,
    db: Session = Depends(get_db),
    payment_id: str,
    refund_data: RefundCreate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Create a refund for a payment
    """
    try:
        # Set payment_id from URL parameter
        refund_data.payment_id = payment_id
        
        payment_service = PaymentService(db)
        refund = await payment_service.create_refund(
            refund_data=refund_data,
            user=current_user
        )
        return refund
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create refund: {str(e)}"
        )


@router.get("/refunds", response_model=RefundList)
def get_refunds(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get user's refund history
    """
    refunds = db.query(Refund).filter(
        Refund.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    total = db.query(Refund).filter(
        Refund.user_id == current_user.id
    ).count()
    
    return RefundList(
        refunds=refunds,
        total=total,
        page=skip // limit + 1,
        per_page=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/refunds/{refund_id}", response_model=RefundSchema)
def get_refund(
    *,
    db: Session = Depends(get_db),
    refund_id: str,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get a specific refund by ID
    """
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    if refund.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this refund"
        )
    
    return refund


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """
    Handle Stripe webhook events
    """
    try:
        # Get the raw payload and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )
        
        payment_service = PaymentService(db)
        result = payment_service.process_webhook(payload, signature)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/config")
def get_payment_config(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get payment configuration for frontend
    """
    from app.core.config import settings
    
    return {
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "currency": settings.STRIPE_CURRENCY,
    } 