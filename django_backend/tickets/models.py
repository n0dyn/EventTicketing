from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid
import string
import secrets


class TicketType(models.Model):
    """
    Model for different types of tickets for an event
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='ticket_types'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField()
    sold_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Sale period
    sale_start = models.DateTimeField(blank=True, null=True)
    sale_end = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ticket Type'
        verbose_name_plural = 'Ticket Types'
        unique_together = ['event', 'name']

    def __str__(self):
        return f"{self.event.title} - {self.name}"

    @property
    def available_quantity(self):
        """Return remaining tickets available"""
        return max(0, self.quantity - self.sold_count)

    @property
    def is_sold_out(self):
        """Check if this ticket type is sold out"""
        return self.sold_count >= self.quantity

    @property
    def is_on_sale(self):
        """Check if tickets are currently on sale"""
        now = timezone.now()
        if self.sale_start and now < self.sale_start:
            return False
        if self.sale_end and now > self.sale_end:
            return False
        return self.is_active and not self.is_sold_out


class PriceTier(models.Model):
    """
    Model for price tiers within a ticket type (early bird, regular, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE,
        related_name='price_tiers'
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(blank=True, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Price Tier'
        verbose_name_plural = 'Price Tiers'
        ordering = ['start_date']

    def __str__(self):
        return f"{self.ticket_type} - {self.name}"

    @property
    def is_active(self):
        """Check if this price tier is currently active"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class PromoCode(models.Model):
    """
    Model for promotional discount codes
    """
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='promo_codes'
    )
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_uses = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'

    def __str__(self):
        return f"{self.code} - {self.event.title}"

    @property
    def is_valid(self):
        """Check if promo code is currently valid"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        return True

    def calculate_discount(self, amount):
        """Calculate discount amount for given price"""
        if not self.is_valid:
            return 0
        
        if self.discount_type == 'percentage':
            return min(amount, amount * (self.discount_value / 100))
        else:  # fixed amount
            return min(amount, self.discount_value)


class Ticket(models.Model):
    """
    Model for individual tickets
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.CASCADE,
        related_name='tickets'
    )
    attendee_name = models.CharField(max_length=255, blank=True)
    attendee_email = models.EmailField(blank=True)
    ticket_code = models.CharField(max_length=20, unique=True)
    qr_code = models.TextField(blank=True)  # Base64 encoded QR code
    
    # Check-in tracking
    is_checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(blank=True, null=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='checked_in_tickets'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'

    def __str__(self):
        return f"Ticket {self.ticket_code} - {self.ticket_type.name}"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = self.generate_ticket_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_ticket_code():
        """Generate a unique ticket code"""
        length = 8
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(length))
            if not Ticket.objects.filter(ticket_code=code).exists():
                return code

    def check_in(self, user=None):
        """Check in this ticket"""
        if not self.is_checked_in:
            self.is_checked_in = True
            self.checked_in_at = timezone.now()
            self.checked_in_by = user
            self.save()

    @property
    def event(self):
        """Get the event for this ticket"""
        return self.ticket_type.event
