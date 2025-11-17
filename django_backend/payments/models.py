from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class PaymentStatus(models.TextChoices):
    """Choices for payment status"""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'
    PARTIALLY_REFUNDED = 'partially_refunded', 'Partially Refunded'


class PaymentProvider(models.TextChoices):
    """Choices for payment providers"""
    STRIPE = 'stripe', 'Stripe'
    PAYPAL = 'paypal', 'PayPal'
    SQUARE = 'square', 'Square'
    MANUAL = 'manual', 'Manual'


class Payment(models.Model):
    """
    Model for payment transactions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Provider information
    provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.STRIPE
    )
    provider_payment_id = models.CharField(max_length=255, blank=True)
    provider_payment_intent_id = models.CharField(max_length=255, blank=True)
    provider_charge_id = models.CharField(max_length=255, blank=True)
    
    # Transaction details
    transaction_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)]
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)]
    )
    
    # Metadata
    payment_method_details = models.JSONField(default=dict, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {str(self.id)[:8]} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        # Calculate net amount after transaction fee
        if self.net_amount is None:
            self.net_amount = max(Decimal('0.00'), self.amount - self.transaction_fee)
        super().save(*args, **kwargs)

    def mark_succeeded(self):
        """Mark payment as succeeded"""
        if self.status != PaymentStatus.SUCCEEDED:
            self.status = PaymentStatus.SUCCEEDED
            self.processed_at = timezone.now()
            self.save()

    def mark_failed(self, reason=""):
        """Mark payment as failed"""
        if self.status != PaymentStatus.FAILED:
            self.status = PaymentStatus.FAILED
            self.failure_reason = reason
            self.processed_at = timezone.now()
            self.save()

    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == PaymentStatus.SUCCEEDED

    @property
    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return self.status in [PaymentStatus.SUCCEEDED, PaymentStatus.PARTIALLY_REFUNDED]


class Refund(models.Model):
    """
    Model for payment refunds
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    
    # Refund details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='USD')
    reason = models.TextField(blank=True)
    
    # Provider information
    provider_refund_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {str(self.id)[:8]} - {self.amount} {self.currency}"

    def mark_succeeded(self):
        """Mark refund as succeeded"""
        if self.status != PaymentStatus.SUCCEEDED:
            self.status = PaymentStatus.SUCCEEDED
            self.processed_at = timezone.now()
            self.save()
            
            # Update payment status
            total_refunded = sum(
                refund.amount for refund in self.payment.refunds.filter(
                    status=PaymentStatus.SUCCEEDED
                )
            )
            if total_refunded >= self.payment.amount:
                self.payment.status = PaymentStatus.REFUNDED
            else:
                self.payment.status = PaymentStatus.PARTIALLY_REFUNDED
            self.payment.save()
