from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class OrderStatus(models.TextChoices):
    """Choices for order status"""
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    REFUNDED = 'refunded', 'Refunded'


class PaymentMethod(models.TextChoices):
    """Choices for payment methods"""
    CREDIT_CARD = 'credit_card', 'Credit Card'
    PAYPAL = 'paypal', 'PayPal'
    BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
    OTHER = 'other', 'Other'


class Order(models.Model):
    """
    Model for customer orders
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='orders'
    )
    
    # Order totals
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)]
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)]
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)]
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Order status and payment
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True
    )
    payment_intent_id = models.CharField(max_length=255, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True, unique=True)
    
    # Billing information
    billing_email = models.EmailField(blank=True)
    billing_first_name = models.CharField(max_length=100, blank=True)
    billing_last_name = models.CharField(max_length=100, blank=True)
    billing_address_line_1 = models.CharField(max_length=255, blank=True)
    billing_address_line_2 = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=100, blank=True)
    billing_state = models.CharField(max_length=100, blank=True)
    billing_postal_code = models.CharField(max_length=20, blank=True)
    billing_country = models.CharField(max_length=100, blank=True)
    
    # Promo code
    promo_code = models.ForeignKey(
        'tickets.PromoCode',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='orders'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {str(self.id)[:8]} - {self.user.email}"

    @property
    def order_number(self):
        """Return a short order number for display"""
        return str(self.id)[:8].upper()

    @property
    def billing_full_name(self):
        """Return full billing name"""
        return f"{self.billing_first_name} {self.billing_last_name}".strip()

    @property
    def billing_address(self):
        """Return formatted billing address"""
        address_parts = [
            self.billing_address_line_1,
            self.billing_address_line_2,
            self.billing_city,
            self.billing_state,
            self.billing_postal_code,
            self.billing_country
        ]
        return ', '.join(filter(None, address_parts))

    def calculate_totals(self):
        """Calculate order totals from line items"""
        self.subtotal = sum(item.total_price for item in self.order_items.all())
        
        # Apply promo code discount
        if self.promo_code and self.promo_code.is_valid:
            self.discount_amount = self.promo_code.calculate_discount(self.subtotal)
        else:
            self.discount_amount = Decimal('0.00')
        
        # Calculate total (tax can be added later)
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        self.save()

    def mark_completed(self):
        """Mark order as completed"""
        if self.status != OrderStatus.COMPLETED:
            self.status = OrderStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save()

    def get_ticket_count(self):
        """Return total number of tickets in this order"""
        return sum(item.quantity for item in self.order_items.all())


class OrderItem(models.Model):
    """
    Model for individual items in an order
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    ticket_type = models.ForeignKey(
        'tickets.TicketType',
        on_delete=models.CASCADE,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        unique_together = ['order', 'ticket_type']

    def __str__(self):
        return f"{self.quantity}x {self.ticket_type.name}"

    def save(self, *args, **kwargs):
        # Auto-calculate total price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Cart(models.Model):
    """
    Model for shopping cart
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart for {self.user.email}"

    @property
    def total_items(self):
        """Return total number of items in cart"""
        return sum(item.quantity for item in self.cart_items.all())

    @property
    def total_amount(self):
        """Return total amount for all items in cart"""
        return sum(item.total_price for item in self.cart_items.all())

    def is_expired(self):
        """Check if cart has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def clear(self):
        """Remove all items from cart"""
        self.cart_items.all().delete()
        self.updated_at = timezone.now()
        self.save()


class CartItem(models.Model):
    """
    Model for items in shopping cart
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    ticket_type = models.ForeignKey(
        'tickets.TicketType',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'ticket_type']

    def __str__(self):
        return f"{self.quantity}x {self.ticket_type.name}"

    @property
    def unit_price(self):
        """Get current price for this ticket type"""
        return self.ticket_type.price

    @property
    def total_price(self):
        """Calculate total price for this cart item"""
        return self.unit_price * self.quantity

    def increase_quantity(self, amount=1):
        """Increase quantity by specified amount"""
        self.quantity += amount
        self.save()

    def decrease_quantity(self, amount=1):
        """Decrease quantity by specified amount"""
        self.quantity = max(0, self.quantity - amount)
        if self.quantity == 0:
            self.delete()
        else:
            self.save()
