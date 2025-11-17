"""
Ticketing System Enhancements
Models, managers, and utilities for advanced ticketing features:
1. Ticket Disabling/Blacklisting
2. User Ban Management
3. Ticket Transfer System
4. Advanced Metrics
"""

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid


# ============================================================================
# 1. TICKET STATUS & DISABLING SYSTEM
# ============================================================================

class TicketStatus(models.TextChoices):
    """Status of a ticket"""
    ACTIVE = 'active', 'Active'
    DISABLED = 'disabled', 'Disabled'
    BLACKLISTED = 'blacklisted', 'Blacklisted'
    REFUNDED = 'refunded', 'Refunded'
    TRANSFERRED = 'transferred', 'Transferred'
    EXPIRED = 'expired', 'Expired'


class TicketDisablement(models.Model):
    """
    Audit trail for ticket disablements
    Records why and by whom tickets were disabled
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.OneToOneField(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='disablement'
    )
    
    # Status information
    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.DISABLED
    )
    
    # Reason for disablement
    DISABILITY_REASONS = [
        ('fraud', 'Fraud Detection'),
        ('duplicate', 'Duplicate Ticket'),
        ('fraud_attempt', 'Fraudulent Purchase'),
        ('refund', 'Refund Processed'),
        ('user_ban', 'User Banned from Event'),
        ('duplicate_entry', 'Duplicate Entry Attempt'),
        ('admin_action', 'Admin Manual Disablement'),
        ('event_cancelled', 'Event Cancelled'),
        ('other', 'Other Reason'),
    ]
    
    reason = models.CharField(
        max_length=50,
        choices=DISABILITY_REASONS
    )
    detailed_reason = models.TextField(help_text='Detailed explanation')
    
    # Who disabled it
    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='disabled_tickets'
    )
    
    # Evidence/documentation
    evidence_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional data supporting the disablement'
    )
    
    # Timeline
    disabled_at = models.DateTimeField(default=timezone.now)
    re_enabled_at = models.DateTimeField(null=True, blank=True)
    re_enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='re_enabled_tickets'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ticket Disablement'
        verbose_name_plural = 'Ticket Disablements'
        ordering = ['-disabled_at']
    
    def __str__(self):
        return f"Disablement of {self.ticket.ticket_code} - {self.reason}"
    
    @property
    def is_active(self):
        """Check if disablement is currently active"""
        return self.re_enabled_at is None
    
    def re_enable(self, user=None):
        """Re-enable a disabled ticket"""
        self.re_enabled_at = timezone.now()
        self.re_enabled_by = user
        self.save()
        # Update ticket status
        self.ticket.status = TicketStatus.ACTIVE
        self.ticket.save()


class TicketBlacklist(models.Model):
    """
    Global or event-specific ticket blacklist
    Prevents specific tickets or ticket patterns from being used
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Scope
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='ticket_blacklists',
        null=True,
        blank=True,
        help_text='Null = global blacklist'
    )
    
    # Ticket reference
    ticket = models.OneToOneField(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='blacklist_entry',
        null=True,
        blank=True
    )
    ticket_code_pattern = models.CharField(
        max_length=50,
        blank=True,
        help_text='Regex pattern for ticket codes'
    )
    
    # Blacklist details
    reason = models.CharField(
        max_length=100,
        help_text='Why this ticket(s) are blacklisted'
    )
    severity = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    
    # Timeline
    blacklisted_at = models.DateTimeField(default=timezone.now)
    blacklisted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blacklisted_tickets'
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Evidence
    evidence = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ticket Blacklist'
        verbose_name_plural = 'Ticket Blacklists'
        indexes = [
            models.Index(fields=['event', 'severity']),
            models.Index(fields=['ticket_code_pattern']),
        ]
    
    def __str__(self):
        if self.ticket:
            return f"Blacklist: {self.ticket.ticket_code}"
        return f"Blacklist: {self.ticket_code_pattern}"
    
    @property
    def is_active(self):
        """Check if blacklist entry is currently active"""
        if self.expires_at:
            return timezone.now() <= self.expires_at
        return True
    
    @classmethod
    def is_ticket_blacklisted(cls, ticket):
        """Check if a specific ticket is blacklisted"""
        # Check direct ticket blacklist
        if cls.objects.filter(
            ticket=ticket,
            event__isnull=True
        ).exists():  # Global blacklist
            return True
        
        if ticket.event and cls.objects.filter(
            ticket=ticket,
            event=ticket.event
        ).exists():  # Event-specific blacklist
            return True
        
        return False


# ============================================================================
# 2. USER BAN MANAGEMENT
# ============================================================================

class BanReason(models.TextChoices):
    """Reasons for banning a user"""
    FRAUD = 'fraud', 'Fraudulent Activity'
    VIOLENCE = 'violence', 'Violence/Threats'
    HARASSMENT = 'harassment', 'Harassment/Abuse'
    POLICY_VIOLATION = 'policy_violation', 'Policy Violation'
    RESELLER = 'reseller', 'Unauthorized Reselling'
    CHARGEBACKING = 'chargebacking', 'Chargeback Fraud'
    TROLLING = 'trolling', 'Trolling/Disruption'
    SPAM = 'spam', 'Spam'
    OTHER = 'other', 'Other'


class UserBan(models.Model):
    """
    Ban a user from specific event or globally
    Prevents banned users from:
    - Purchasing tickets
    - Accessing events
    - Re-entering
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User and scope
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bans'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='user_bans',
        null=True,
        blank=True,
        help_text='Null = global ban'
    )
    
    # Ban details
    reason = models.CharField(max_length=50, choices=BanReason.choices)
    description = models.TextField(help_text='Detailed reason for ban')
    
    # Evidence
    evidence = models.JSONField(default=dict, blank=True)
    
    # Duration
    ban_issued_at = models.DateTimeField(default=timezone.now)
    ban_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Null = permanent ban'
    )
    
    # Who issued it
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_bans'
    )
    
    # Appeal
    appeal_requested_at = models.DateTimeField(null=True, blank=True)
    appeal_notes = models.TextField(blank=True)
    appeal_reviewed_at = models.DateTimeField(null=True, blank=True)
    appeal_approved = models.BooleanField(null=True, blank=True)
    appeal_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_appeals'
    )
    
    # Lift ban
    lifted_at = models.DateTimeField(null=True, blank=True)
    lifted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lifted_bans'
    )
    lift_reason = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Ban'
        verbose_name_plural = 'User Bans'
        unique_together = [['user', 'event']]  # One ban per user per event
        ordering = ['-ban_issued_at']
        indexes = [
            models.Index(fields=['user', 'event']),
            models.Index(fields=['ban_until']),
        ]
    
    def __str__(self):
        scope = self.event.title if self.event else 'Global'
        return f"Ban: {self.user.email} from {scope}"
    
    @property
    def is_active(self):
        """Check if ban is currently active"""
        if self.lifted_at:
            return False
        
        if self.appeal_approved:
            return False
        
        if self.ban_until:
            return timezone.now() <= self.ban_until
        
        return True
    
    @property
    def is_permanent(self):
        """Check if this is a permanent ban"""
        return self.ban_until is None
    
    @property
    def days_remaining(self):
        """Get days remaining for non-permanent bans"""
        if not self.ban_until:
            return None
        days = (self.ban_until - timezone.now()).days
        return max(0, days)
    
    def request_appeal(self, notes=''):
        """Request an appeal"""
        self.appeal_requested_at = timezone.now()
        self.appeal_notes = notes
        self.save()
    
    def approve_appeal(self, reviewer=None):
        """Approve appeal and lift ban"""
        self.appeal_approved = True
        self.appeal_reviewed_at = timezone.now()
        self.appeal_reviewed_by = reviewer
        self.lifted_at = timezone.now()
        self.lifted_by = reviewer
        self.lift_reason = 'Appeal approved'
        self.save()
    
    def reject_appeal(self, reviewer=None):
        """Reject appeal"""
        self.appeal_approved = False
        self.appeal_reviewed_at = timezone.now()
        self.appeal_reviewed_by = reviewer
        self.save()
    
    def lift(self, user=None, reason='Manual lift'):
        """Lift a ban"""
        self.lifted_at = timezone.now()
        self.lifted_by = user
        self.lift_reason = reason
        self.save()
    
    @classmethod
    def is_user_banned(cls, user, event=None):
        """
        Check if user is banned
        If event specified, checks event ban
        Otherwise checks global ban
        """
        bans = cls.objects.filter(user=user)
        
        if event:
            # Check event-specific ban
            bans = bans.filter(event=event)
        else:
            # Check global ban
            bans = bans.filter(event__isnull=True)
        
        for ban in bans:
            if ban.is_active:
                return True
        
        return False


# ============================================================================
# 3. TICKET TRANSFER SYSTEM
# ============================================================================

class TicketTransfer(models.Model):
    """
    Track ticket transfers between users
    Support gifting and resale
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ticket info
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='transfers'
    )
    
    # Transfer parties
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_sent'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_received'
    )
    
    # Transfer type
    TRANSFER_TYPES = [
        ('gift', 'Gift'),
        ('resale', 'Resale'),
        ('admin', 'Admin Transfer'),
        ('correction', 'Correction'),
    ]
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPES)
    
    # Resale pricing (if resale)
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    resale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    platform_fee_percent = models.FloatField(default=10.0)
    platform_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Status
    TRANSFER_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=TRANSFER_STATUS,
        default='pending'
    )
    
    # Dates
    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # QR code regeneration
    regenerate_qr = models.BooleanField(default=True)
    old_qr_code = models.ForeignKey(
        'attendees.TicketQRCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfer_old_qr'
    )
    new_qr_code = models.ForeignKey(
        'attendees.TicketQRCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfer_new_qr'
    )
    
    # Notes
    transfer_notes = models.TextField(blank=True)
    decline_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ticket Transfer'
        verbose_name_plural = 'Ticket Transfers'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['ticket', 'status']),
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
        ]
    
    def __str__(self):
        return f"Transfer of {self.ticket.ticket_code} from {self.from_user.email} to {self.to_user.email}"
    
    @property
    def is_expired(self):
        """Check if transfer offer has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Accept the transfer"""
        if self.status != 'pending':
            return False
        
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.ticket.to_user = self.to_user
        
        # Regenerate QR if needed
        if self.regenerate_qr:
            # Create new QR code for new user
            # This would typically be done via signal
            pass
        
        self.save()
        self.ticket.save()
        return True
    
    def decline(self, reason=''):
        """Decline the transfer"""
        if self.status != 'pending':
            return False
        
        self.status = 'declined'
        self.decline_reason = reason
        self.save()
        return True
    
    def complete(self):
        """Mark transfer as completed"""
        if self.status != 'accepted':
            return False
        
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
        return True


# ============================================================================
# 4. ADVANCED METRICS
# ============================================================================

class EventMetrics(models.Model):
    """
    Comprehensive event metrics and analytics
    Updated in real-time or via background tasks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Revenue metrics
    total_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Total revenue from ticket sales'
    )
    revenue_by_ticket_type = models.JSONField(
        default=dict,
        blank=True,
        help_text='Revenue breakdown by ticket type'
    )
    refund_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    avg_ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Attendance metrics
    total_purchased = models.PositiveIntegerField(default=0)
    total_attended = models.PositiveIntegerField(default=0)
    no_show_rate = models.FloatField(default=0.0, help_text='Percentage')
    no_show_count = models.PositiveIntegerField(default=0)
    late_arrival_count = models.PositiveIntegerField(default=0)
    late_arrival_percentage = models.FloatField(default=0.0)
    
    # Conversion metrics
    registration_to_purchase_rate = models.FloatField(default=0.0)
    waitlist_to_purchase_rate = models.FloatField(default=0.0)
    promo_code_usage_rate = models.FloatField(default=0.0)
    payment_failure_rate = models.FloatField(default=0.0)
    
    # Fraud metrics
    suspicious_transactions = models.PositiveIntegerField(default=0)
    duplicate_ticket_attempts = models.PositiveIntegerField(default=0)
    refund_rate = models.FloatField(default=0.0, help_text='% of tickets refunded')
    banned_user_entry_attempts = models.PositiveIntegerField(default=0)
    
    # Demographics (if collected)
    age_distribution = models.JSONField(default=dict, blank=True)
    geographic_distribution = models.JSONField(default=dict, blank=True)
    repeat_attendee_rate = models.FloatField(default=0.0)
    
    # Traffic patterns
    peak_entry_time = models.TimeField(null=True, blank=True)
    peak_exit_time = models.TimeField(null=True, blank=True)
    avg_session_duration = models.DurationField(null=True, blank=True)
    busiest_day_of_week = models.CharField(max_length=10, blank=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Event Metrics'
        verbose_name_plural = 'Event Metrics'
    
    def __str__(self):
        return f"Metrics for {self.event.title}"


class LocationMetrics(models.Model):
    """
    Per-location check-in metrics
    Track efficiency and flow at each gate
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(
        'attendees.CheckInLocation',
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='location_metrics'
    )
    
    # Flow metrics
    total_entries = models.PositiveIntegerField(default=0)
    total_exits = models.PositiveIntegerField(default=0)
    peak_flow_time = models.TimeField(null=True, blank=True)
    avg_processing_time = models.FloatField(default=0.0, help_text='Seconds per person')
    
    # By ticket type
    entries_by_ticket_type = models.JSONField(default=dict, blank=True)
    entries_by_access_level = models.JSONField(default=dict, blank=True)
    
    # Performance
    success_rate = models.FloatField(default=100.0, help_text='% successful scans')
    error_count = models.PositiveIntegerField(default=0)
    
    # Date tracking
    date = models.DateField()
    hour = models.PositiveIntegerField(null=True, blank=True)  # For hourly breakdown
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Location Metrics'
        verbose_name_plural = 'Location Metrics'
        unique_together = [['location', 'date', 'hour']]
        ordering = ['-date', 'hour']
    
    def __str__(self):
        return f"{self.location.name} - {self.date}"

