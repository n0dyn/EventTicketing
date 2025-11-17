from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid


class Attendee(models.Model):
    """
    Model for event attendees
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='attendees'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendee_records',
        blank=True,
        null=True
    )
    ticket = models.OneToOneField(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='attendee',
        blank=True,
        null=True
    )
    
    # Personal information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Additional information
    company = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    dietary_requirements = models.TextField(blank=True)
    special_needs = models.TextField(blank=True)
    
    # Check-in tracking
    is_checked_in = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(blank=True, null=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='checked_in_attendees'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Attendee'
        verbose_name_plural = 'Attendees'
        unique_together = ['event', 'email']
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"

    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"

    def check_in(self, user=None):
        """Check in this attendee"""
        if not self.is_checked_in:
            self.is_checked_in = True
            self.check_in_time = timezone.now()
            self.checked_in_by = user
            self.save()
            
            # Also check in the associated ticket if it exists
            if self.ticket:
                self.ticket.check_in(user)

    def check_out(self):
        """Check out this attendee (undo check-in)"""
        if self.is_checked_in:
            self.is_checked_in = False
            self.check_in_time = None
            self.checked_in_by = None
            self.save()

    @property
    def ticket_type_name(self):
        """Get the ticket type name"""
        if self.ticket and self.ticket.ticket_type:
            return self.ticket.ticket_type.name
        return "No Ticket"


class CheckInStatus(models.TextChoices):
    """Status of check-in attempts"""
    PENDING = 'pending', 'Pending'
    CHECKED_IN = 'checked_in', 'Checked In'
    CHECKED_OUT = 'checked_out', 'Checked Out'
    INVALID = 'invalid', 'Invalid'
    EXPIRED = 'expired', 'Expired'
    DUPLICATE = 'duplicate', 'Duplicate'


class AccessLevel(models.TextChoices):
    """Access levels for different areas"""
    GENERAL = 'general', 'General'
    VIP = 'vip', 'VIP'
    BACKSTAGE = 'backstage', 'Backstage'
    STAFF = 'staff', 'Staff'
    PRESS = 'press', 'Press'


class ScanResult(models.TextChoices):
    """Results of QR code scanning"""
    SUCCESS = 'success', 'Success'
    INVALID_CODE = 'invalid_code', 'Invalid Code'
    EXPIRED_TICKET = 'expired_ticket', 'Expired Ticket'
    ALREADY_USED = 'already_used', 'Already Used'
    EVENT_NOT_STARTED = 'event_not_started', 'Event Not Started'
    EVENT_ENDED = 'event_ended', 'Event Ended'
    WRONG_EVENT = 'wrong_event', 'Wrong Event'
    INSUFFICIENT_ACCESS = 'insufficient_access', 'Insufficient Access'
    SYSTEM_ERROR = 'system_error', 'System Error'


class TicketQRCode(models.Model):
    """
    QR code data for tickets
    Stores secure QR codes and validates them for check-in
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ticket association
    ticket = models.OneToOneField(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='qr_code_data'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='qr_codes'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='qr_codes'
    )
    
    # QR code data
    qr_code_data = models.CharField(max_length=500, unique=True, db_index=True)
    qr_code_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Security and validation
    secret_key = models.CharField(max_length=64)
    validation_data = models.JSONField(default=dict, blank=True, help_text='Additional validation info')
    
    # Access control
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.GENERAL
    )
    restricted_areas = models.JSONField(default=list, blank=True, help_text='List of accessible areas')
    
    # Status and usage
    is_active = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1, help_text='How many times can be scanned')
    current_usage = models.PositiveIntegerField(default=0)
    
    # Timing
    valid_from = models.DateTimeField(blank=True, null=True, help_text='When QR becomes valid')
    valid_until = models.DateTimeField(blank=True, null=True, help_text='When QR expires')
    
    # Generation metadata
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='generated_qr_codes'
    )
    version = models.PositiveIntegerField(default=1, help_text='For QR code format versioning')

    class Meta:
        verbose_name = 'Ticket QR Code'
        verbose_name_plural = 'Ticket QR Codes'
        ordering = ['-generated_at']

    def __str__(self):
        return f"QR Code for {self.ticket.ticket_code}"

    @property
    def is_valid(self):
        """Check if QR code is currently valid"""
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_until and now > self.valid_until:
            return False
        
        if self.current_usage >= self.usage_limit:
            return False
        
        return True

    @property
    def can_be_used(self):
        """Check if QR code can still be used"""
        return self.is_valid and self.current_usage < self.usage_limit

    def generate_qr_data(self):
        """Generate secure QR code data"""
        import hashlib
        timestamp = int(timezone.now().timestamp())
        
        data_components = [
            str(self.ticket.id),
            str(self.event.id),
            str(timestamp),
            self.secret_key[:8]  # First 8 chars of secret for validation
        ]
        
        # Create QR data string
        qr_data = "|".join(data_components)
        
        # Add checksum for integrity
        checksum = hashlib.sha256(f"{qr_data}:{self.secret_key}".encode()).hexdigest()[:8]
        
        return f"{qr_data}|{checksum}"

    def validate_qr_data(self, scanned_data):
        """Validate scanned QR code data"""
        import hashlib
        try:
            parts = scanned_data.split("|")
            if len(parts) != 5:  # ticket_id, event_id, timestamp, secret_part, checksum
                return False
            
            ticket_id, event_id, timestamp, secret_part, checksum = parts
            
            # Verify ticket and event match
            if ticket_id != str(self.ticket.id) or event_id != str(self.event.id):
                return False
            
            # Verify secret part
            if secret_part != self.secret_key[:8]:
                return False
            
            # Verify checksum
            qr_data = "|".join(parts[:-1])
            expected_checksum = hashlib.sha256(f"{qr_data}:{self.secret_key}".encode()).hexdigest()[:8]
            
            return checksum == expected_checksum
            
        except Exception:
            return False

    def increment_usage(self):
        """Increment usage count"""
        self.current_usage += 1
        self.save(update_fields=['current_usage'])


class CheckInLocation(models.Model):
    """
    Defines check-in locations and gates for events
    Allows multiple entry/exit points with different access controls
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event association
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='check_in_locations'
    )
    
    # Location details
    name = models.CharField(max_length=255, help_text='Main Entrance, VIP Gate, etc.')
    description = models.TextField(blank=True)
    location_type = models.CharField(
        max_length=20,
        choices=[
            ('entrance', 'Entrance'),
            ('exit', 'Exit'),
            ('checkpoint', 'Checkpoint'),
        ],
        default='entrance'
    )
    
    # Access control
    required_access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.GENERAL
    )
    allowed_ticket_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allowed ticket type IDs'
    )
    
    # Capacity and flow control
    max_capacity = models.PositiveIntegerField(blank=True, null=True)
    current_occupancy = models.PositiveIntegerField(default=0)
    
    # Timing
    opens_at = models.DateTimeField(blank=True, null=True)
    closes_at = models.DateTimeField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_monitored = models.BooleanField(default=True, help_text='Track occupancy')
    
    # Physical location
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    geofence_radius = models.FloatField(default=50.0, help_text='Meters')
    
    # Configuration
    settings = models.JSONField(default=dict, blank=True, help_text='Additional location settings')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Check In Location'
        verbose_name_plural = 'Check In Locations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    @property
    def is_open(self):
        """Check if location is currently open"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        
        if self.opens_at and now < self.opens_at:
            return False
        
        if self.closes_at and now > self.closes_at:
            return False
        
        return True

    @property
    def is_at_capacity(self):
        """Check if location is at capacity"""
        if not self.max_capacity:
            return False
        return self.current_occupancy >= self.max_capacity


class ScanSession(models.Model):
    """
    Tracks scanning sessions for event staff
    Manages scanner device authentication and session data
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session details
    session_token = models.CharField(max_length=64, unique=True, db_index=True)
    device_id = models.CharField(max_length=255)
    device_name = models.CharField(max_length=255, blank=True)
    
    # User and event
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_sessions'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='scan_sessions'
    )
    location = models.ForeignKey(
        CheckInLocation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='scan_sessions'
    )
    
    # Session status
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(blank=True, null=True)
    
    # Statistics
    scans_performed = models.PositiveIntegerField(default=0)
    successful_scans = models.PositiveIntegerField(default=0)
    failed_scans = models.PositiveIntegerField(default=0)
    
    # Device info
    device_info = models.JSONField(default=dict, blank=True, help_text='Browser, OS, etc.')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scan Session'
        verbose_name_plural = 'Scan Sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"Scan Session: {self.user.email} - {self.event.title}"

    @classmethod
    def generate_session_token(cls):
        """Generate secure session token"""
        import secrets
        return secrets.token_urlsafe(32)

    @property
    def success_rate(self):
        """Calculate scan success rate"""
        if self.scans_performed == 0:
            return 0.0
        return (self.successful_scans / self.scans_performed) * 100

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class CheckIn(models.Model):
    """
    Records of attendee check-ins and check-outs
    Tracks when and where attendees enter/exit events
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # References
    qr_code = models.ForeignKey(
        TicketQRCode,
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    
    # Check-in details
    status = models.CharField(
        max_length=20,
        choices=CheckInStatus.choices,
        default=CheckInStatus.PENDING
    )
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(blank=True, null=True)
    
    # Location and device info
    check_in_location = models.CharField(max_length=255, blank=True, help_text='Gate/entrance name')
    scanner_device_id = models.CharField(max_length=255, blank=True, help_text='Device that scanned')
    scanner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='performed_check_ins'
    )
    
    # Geolocation (if enabled)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    accuracy = models.FloatField(blank=True, null=True)
    
    # Additional data
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional scan data')
    
    # Validation results
    scan_result = models.CharField(
        max_length=30,
        choices=ScanResult.choices,
        default=ScanResult.SUCCESS
    )
    validation_errors = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Check In'
        verbose_name_plural = 'Check Ins'
        ordering = ['-check_in_time']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['user', 'check_in_time']),
        ]

    def __str__(self):
        return f"Check-in: {self.user.email} at {self.check_in_time}"

    @property
    def duration_at_event(self):
        """Calculate time spent at event"""
        if not self.check_out_time:
            return None
        return self.check_out_time - self.check_in_time

    @property
    def is_currently_checked_in(self):
        """Check if attendee is currently at the event"""
        return self.status == CheckInStatus.CHECKED_IN and not self.check_out_time

    def check_out(self):
        """Check out the attendee"""
        if self.status == CheckInStatus.CHECKED_IN:
            self.status = CheckInStatus.CHECKED_OUT
            self.check_out_time = timezone.now()
            self.save()


class CheckInStats(models.Model):
    """
    Aggregated check-in statistics for events
    Provides real-time analytics for event monitoring
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='check_in_stats'
    )
    
    # Current status
    total_tickets = models.PositiveIntegerField(default=0)
    checked_in_count = models.PositiveIntegerField(default=0)
    checked_out_count = models.PositiveIntegerField(default=0)
    currently_at_event = models.PositiveIntegerField(default=0)
    
    # Peak metrics
    peak_occupancy = models.PositiveIntegerField(default=0)
    peak_occupancy_time = models.DateTimeField(blank=True, null=True)
    
    # Flow metrics
    average_check_in_time = models.FloatField(default=0.0, help_text='Seconds')
    busiest_entrance = models.CharField(max_length=255, blank=True)
    busiest_hour = models.PositiveIntegerField(blank=True, null=True, help_text='Hour of day (0-23)')
    
    # Conversion metrics
    no_show_count = models.PositiveIntegerField(default=0)
    late_arrival_count = models.PositiveIntegerField(default=0, help_text='Arrived after event started')
    
    # Time-based breakdowns
    hourly_check_ins = models.JSONField(default=dict, blank=True, help_text='Check-ins by hour')
    location_breakdown = models.JSONField(default=dict, blank=True, help_text='Check-ins by location')
    
    # Last update
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Check In Stats'
        verbose_name_plural = 'Check In Stats'

    def __str__(self):
        return f"Check-in Stats for {self.event.title}"

    @property
    def attendance_rate(self):
        """Calculate attendance rate percentage"""
        if self.total_tickets == 0:
            return 0.0
        return (self.checked_in_count / self.total_tickets) * 100

    @property
    def current_occupancy_rate(self):
        """Calculate current occupancy as percentage of capacity"""
        if self.total_tickets == 0:
            return 0.0
        return (self.currently_at_event / self.total_tickets) * 100

    def update_stats(self):
        """Update all statistics"""
        # This would typically be called by a background task
        # or signal handler to keep stats up to date
        self.last_updated = timezone.now()
        self.save()


class WaitlistStatus(models.TextChoices):
    """Status of waitlist entries"""
    ACTIVE = 'active', 'Active'
    NOTIFIED = 'notified', 'Notified'
    CONVERTED = 'converted', 'Converted'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class WaitlistPriority(models.TextChoices):
    """Priority levels for waitlist entries"""
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'
    VIP = 'vip', 'VIP'
    STAFF = 'staff', 'Staff'


class EventWaitlist(models.Model):
    """
    Represents a waitlist for a specific event
    Manages overall waitlist settings and statistics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='waitlist'
    )
    
    # Waitlist settings
    is_enabled = models.BooleanField(default=True)
    max_capacity = models.PositiveIntegerField(blank=True, null=True, help_text='Max waitlist size')
    auto_notify = models.BooleanField(default=True, help_text='Auto-notify when tickets available')
    notification_window_hours = models.PositiveIntegerField(default=24, help_text='How long users have to respond')
    
    # Priority settings
    enable_priority_queue = models.BooleanField(default=False)
    vip_percentage = models.FloatField(default=0.1, help_text='% of releases for VIP users')
    
    # Notification settings
    notification_template_id = models.CharField(max_length=255, blank=True)
    custom_message = models.TextField(blank=True)
    
    # Statistics (updated via signals or background jobs)
    total_entries = models.PositiveIntegerField(default=0)
    active_entries = models.PositiveIntegerField(default=0)
    converted_entries = models.PositiveIntegerField(default=0)
    conversion_rate = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Waitlist'
        verbose_name_plural = 'Event Waitlists'

    def __str__(self):
        return f"Waitlist for {self.event.title}"

    @property
    def current_position_count(self):
        """Get current number of active waitlist entries"""
        return self.entries.filter(status=WaitlistStatus.ACTIVE).count()

    @property
    def is_full(self):
        """Check if waitlist has reached capacity"""
        if not self.max_capacity:
            return False
        return self.current_position_count >= self.max_capacity

    def get_next_position(self):
        """Get the next position number for new entries"""
        active_entries = self.entries.filter(status=WaitlistStatus.ACTIVE)
        if not active_entries.exists():
            return 1
        return active_entries.aggregate(max_pos=models.Max('position'))['max_pos'] + 1

    def update_statistics(self):
        """Update waitlist statistics"""
        self.total_entries = self.entries.count()
        self.active_entries = self.entries.filter(status=WaitlistStatus.ACTIVE).count()
        self.converted_entries = self.entries.filter(status=WaitlistStatus.CONVERTED).count()
        
        if self.total_entries > 0:
            self.conversion_rate = (self.converted_entries / self.total_entries) * 100
        else:
            self.conversion_rate = 0.0
        
        self.save(update_fields=['total_entries', 'active_entries', 'converted_entries', 'conversion_rate'])


class WaitlistEntry(models.Model):
    """
    Individual waitlist entry for a user
    Tracks position, priority, and notification history
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # References
    waitlist = models.ForeignKey(
        EventWaitlist,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
        blank=True,
        null=True
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='waitlist_entries'
    )
    
    # Position and priority
    position = models.PositiveIntegerField()
    priority = models.CharField(
        max_length=20,
        choices=WaitlistPriority.choices,
        default=WaitlistPriority.NORMAL
    )
    priority_score = models.FloatField(default=0.0, help_text='Custom priority scoring')
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=WaitlistStatus.choices,
        default=WaitlistStatus.ACTIVE
    )
    joined_at = models.DateTimeField(default=timezone.now)
    notified_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    converted_at = models.DateTimeField(blank=True, null=True)
    
    # User preferences
    requested_tickets = models.PositiveIntegerField(default=1)
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Maximum price willing to pay'
    )
    preferred_ticket_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of preferred ticket type IDs'
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Additional data
    source = models.CharField(max_length=50, blank=True, help_text='How they joined (web, mobile, admin)')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional custom data')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Waitlist Entry'
        verbose_name_plural = 'Waitlist Entries'
        ordering = ['position']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['priority', 'position']),
        ]

    def __str__(self):
        return f"Waitlist Entry #{self.position} - {self.event.title}"

    @property
    def is_active(self):
        """Check if entry is still active"""
        return self.status == WaitlistStatus.ACTIVE

    @property
    def is_expired(self):
        """Check if notification has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def time_on_waitlist(self):
        """Get time spent on waitlist"""
        end_time = self.converted_at or self.notified_at or timezone.now()
        return end_time - self.joined_at

    def calculate_effective_position(self):
        """Calculate position considering priority"""
        if self.priority == WaitlistPriority.STAFF:
            return 0  # Staff always first
        elif self.priority == WaitlistPriority.VIP:
            return self.position * 0.5  # VIP gets 50% boost
        elif self.priority == WaitlistPriority.HIGH:
            return self.position * 0.8  # High priority gets 20% boost
        else:
            return self.position

    def mark_notified(self, expires_in_hours=24):
        """Mark entry as notified and set expiration"""
        self.status = WaitlistStatus.NOTIFIED
        self.notified_at = timezone.now()
        self.expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)
        self.save()

    def mark_converted(self):
        """Mark entry as converted (user purchased ticket)"""
        self.status = WaitlistStatus.CONVERTED
        self.converted_at = timezone.now()
        self.save()

    def mark_expired(self):
        """Mark entry as expired"""
        self.status = WaitlistStatus.EXPIRED
        self.save()

    def mark_cancelled(self):
        """Mark entry as cancelled by user"""
        self.status = WaitlistStatus.CANCELLED
        self.save()


class WaitlistNotification(models.Model):
    """
    Tracks notifications sent to waitlist users
    Handles notification delivery and response tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # References
    waitlist = models.ForeignKey(
        EventWaitlist,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    entry = models.ForeignKey(
        WaitlistEntry,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waitlist_notifications'
    )
    
    # Notification details
    notification_type = models.CharField(max_length=50, help_text='email, sms, push, etc.')
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    
    # Tickets available
    available_tickets = models.PositiveIntegerField()
    ticket_types = models.JSONField(default=list, blank=True, help_text='Available ticket types')
    special_offer = models.JSONField(default=dict, blank=True, help_text='Special pricing or conditions')
    
    # Timing
    sent_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    
    # Response tracking
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    response_action = models.CharField(max_length=50, blank=True, help_text='purchased, declined, expired')
    
    # Delivery status
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('bounced', 'Bounced'),
        ],
        default='sent'
    )
    delivery_attempts = models.PositiveIntegerField(default=1)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Waitlist Notification'
        verbose_name_plural = 'Waitlist Notifications'
        ordering = ['-sent_at']

    def __str__(self):
        return f"Notification to {self.user.email} - {self.event.title}"

    @property
    def is_expired(self):
        """Check if notification has expired"""
        return timezone.now() > self.expires_at

    @property
    def response_time(self):
        """Get time taken to respond"""
        if not self.responded_at:
            return None
        return self.responded_at - self.sent_at

    def mark_opened(self):
        """Mark notification as opened"""
        if not self.opened_at:
            self.opened_at = timezone.now()
            self.save(update_fields=['opened_at'])

    def mark_clicked(self):
        """Mark notification as clicked"""
        if not self.clicked_at:
            self.clicked_at = timezone.now()
            self.save(update_fields=['clicked_at'])

    def mark_responded(self, action):
        """Mark notification as responded"""
        self.responded_at = timezone.now()
        self.response_action = action
        self.save(update_fields=['responded_at', 'response_action'])


class WaitlistRelease(models.Model):
    """
    Tracks ticket releases and waitlist processing
    Records when tickets become available and how they're distributed
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event and tickets
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='waitlist_releases'
    )
    waitlist = models.ForeignKey(
        EventWaitlist,
        on_delete=models.CASCADE,
        related_name='releases'
    )
    
    # Release details
    tickets_released = models.PositiveIntegerField()
    ticket_type = models.ForeignKey(
        'tickets.TicketType',
        on_delete=models.CASCADE,
        related_name='waitlist_releases',
        blank=True,
        null=True
    )
    release_reason = models.CharField(
        max_length=50,
        choices=[
            ('cancellation', 'Cancellation'),
            ('new_inventory', 'New Inventory'),
            ('admin_release', 'Admin Release'),
            ('other', 'Other'),
        ]
    )
    
    # Processing details
    processed_at = models.DateTimeField(default=timezone.now)
    processing_method = models.CharField(
        max_length=20,
        choices=[
            ('fifo', 'First In, First Out'),
            ('priority', 'Priority Based'),
            ('random', 'Random'),
        ],
        default='fifo'
    )
    
    # Results
    notifications_sent = models.PositiveIntegerField(default=0)
    successful_conversions = models.PositiveIntegerField(default=0)
    failed_notifications = models.PositiveIntegerField(default=0)
    
    # Priority distribution
    vip_notifications = models.PositiveIntegerField(default=0)
    regular_notifications = models.PositiveIntegerField(default=0)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='created_waitlist_releases'
    )
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Waitlist Release'
        verbose_name_plural = 'Waitlist Releases'
        ordering = ['-processed_at']

    def __str__(self):
        return f"Release of {self.tickets_released} tickets for {self.event.title}"

    @property
    def conversion_rate(self):
        """Calculate conversion rate for this release"""
        if self.notifications_sent == 0:
            return 0.0
        return (self.successful_conversions / self.notifications_sent) * 100


class WaitlistPreference(models.Model):
    """
    User-specific waitlist preferences and settings
    Allows users to customize their waitlist experience
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waitlist_preferences'
    )
    
    # Global notification preferences
    default_email_notifications = models.BooleanField(default=True)
    default_sms_notifications = models.BooleanField(default=False)
    default_push_notifications = models.BooleanField(default=True)
    
    # Response time preferences
    preferred_notification_window = models.PositiveIntegerField(default=24, help_text='Hours')
    auto_purchase_enabled = models.BooleanField(default=False, help_text='Auto-purchase when notified')
    auto_purchase_max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Priority settings (for eligible users)
    priority_eligible = models.BooleanField(default=False)
    priority_level = models.CharField(
        max_length=20,
        choices=WaitlistPriority.choices,
        default=WaitlistPriority.NORMAL
    )
    priority_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Communication preferences
    preferred_notification_time_start = models.PositiveIntegerField(default=9, help_text='9 AM')
    preferred_notification_time_end = models.PositiveIntegerField(default=21, help_text='9 PM')
    timezone_field = models.CharField(max_length=50, default='UTC')
    
    # Statistics
    total_waitlist_joins = models.PositiveIntegerField(default=0)
    successful_conversions = models.PositiveIntegerField(default=0)
    average_wait_time_hours = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Waitlist Preference'
        verbose_name_plural = 'Waitlist Preferences'

    def __str__(self):
        return f"Waitlist Preferences for {self.user.email}"

    @property
    def conversion_rate(self):
        """Calculate user's historical conversion rate"""
        if self.total_waitlist_joins == 0:
            return 0.0
        return (self.successful_conversions / self.total_waitlist_joins) * 100
