from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class NotificationType(models.TextChoices):
    """Types of notifications"""
    EMAIL = 'email', 'Email'
    SMS = 'sms', 'SMS'
    PUSH = 'push', 'Push Notification'
    IN_APP = 'in_app', 'In-App Notification'
    WEBHOOK = 'webhook', 'Webhook'


class NotificationStatus(models.TextChoices):
    """Status of notifications"""
    PENDING = 'pending', 'Pending'
    SENT = 'sent', 'Sent'
    DELIVERED = 'delivered', 'Delivered'
    FAILED = 'failed', 'Failed'
    BOUNCED = 'bounced', 'Bounced'
    CANCELLED = 'cancelled', 'Cancelled'


class NotificationPriority(models.TextChoices):
    """Priority levels for notifications"""
    LOW = 'low', 'Low'
    NORMAL = 'normal', 'Normal'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'


class EmailTemplate(models.Model):
    """
    Email templates for different notification types
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    
    # Template metadata
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Template variables (JSON list of variable names)
    variables = models.JSONField(default=list, blank=True, help_text='Available template variables')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='created_email_templates'
    )

    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['name']

    def __str__(self):
        return self.name


class NotificationTemplate(models.Model):
    """
    Templates for different types of notifications
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )
    
    # Template content
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    
    # Email-specific fields
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='notification_templates'
    )
    
    # Template metadata
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Template variables
    variables = models.JSONField(default=list, blank=True, help_text='Available template variables')
    
    # Delivery settings
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    retry_attempts = models.PositiveIntegerField(default=3)
    retry_delay_minutes = models.PositiveIntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='created_notification_templates'
    )

    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"


class Notification(models.Model):
    """
    Individual notifications sent to users
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Template reference
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='notifications'
    )
    
    # Status and delivery
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    
    # Delivery tracking
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    
    # Retry logic
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    next_retry_at = models.DateTimeField(blank=True, null=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Additional data
    data = models.JSONField(default=dict, blank=True, help_text='Additional notification data')
    metadata = models.JSONField(default=dict, blank=True, help_text='Delivery metadata')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_sent(self):
        """Mark notification as sent"""
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_delivered(self):
        """Mark notification as delivered"""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])

    def mark_failed(self, error_message="", error_code=""):
        """Mark notification as failed"""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.error_code = error_code
        self.save(update_fields=['status', 'error_message', 'error_code'])

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

    def should_retry(self):
        """Check if notification should be retried"""
        return (
            self.status == NotificationStatus.FAILED and
            self.retry_count < self.max_retries and
            (not self.next_retry_at or timezone.now() >= self.next_retry_at)
        )

    def schedule_retry(self, delay_minutes=None):
        """Schedule a retry for failed notification"""
        if delay_minutes is None:
            delay_minutes = 5  # Default delay
        
        self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        self.retry_count += 1
        self.status = NotificationStatus.PENDING
        self.save(update_fields=['next_retry_at', 'retry_count', 'status'])


class NotificationPreference(models.Model):
    """
    User notification preferences
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_marketing = models.BooleanField(default=True)
    email_event_updates = models.BooleanField(default=True)
    email_order_updates = models.BooleanField(default=True)
    email_waitlist_updates = models.BooleanField(default=True)
    
    # SMS preferences
    sms_enabled = models.BooleanField(default=False)
    sms_phone = models.CharField(max_length=20, blank=True)
    sms_marketing = models.BooleanField(default=False)
    sms_event_reminders = models.BooleanField(default=True)
    sms_order_updates = models.BooleanField(default=True)
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=True)
    push_marketing = models.BooleanField(default=True)
    push_event_updates = models.BooleanField(default=True)
    push_order_updates = models.BooleanField(default=True)
    push_waitlist_updates = models.BooleanField(default=True)
    
    # In-app notification preferences
    in_app_enabled = models.BooleanField(default=True)
    in_app_marketing = models.BooleanField(default=True)
    in_app_event_updates = models.BooleanField(default=True)
    in_app_order_updates = models.BooleanField(default=True)
    
    # Frequency preferences
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('never', 'Never'),
        ],
        default='daily'
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(blank=True, null=True)
    quiet_hours_end = models.TimeField(blank=True, null=True)
    quiet_hours_timezone = models.CharField(max_length=50, default='UTC')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"

    def is_notification_allowed(self, notification_type, category='general'):
        """Check if notification is allowed based on preferences"""
        if notification_type == NotificationType.EMAIL:
            if not self.email_enabled:
                return False
            if category == 'marketing' and not self.email_marketing:
                return False
            if category == 'event' and not self.email_event_updates:
                return False
            if category == 'order' and not self.email_order_updates:
                return False
            if category == 'waitlist' and not self.email_waitlist_updates:
                return False
        
        elif notification_type == NotificationType.SMS:
            if not self.sms_enabled or not self.sms_phone:
                return False
            if category == 'marketing' and not self.sms_marketing:
                return False
            if category == 'event' and not self.sms_event_reminders:
                return False
            if category == 'order' and not self.sms_order_updates:
                return False
        
        elif notification_type == NotificationType.PUSH:
            if not self.push_enabled:
                return False
            if category == 'marketing' and not self.push_marketing:
                return False
            if category == 'event' and not self.push_event_updates:
                return False
            if category == 'order' and not self.push_order_updates:
                return False
            if category == 'waitlist' and not self.push_waitlist_updates:
                return False
        
        elif notification_type == NotificationType.IN_APP:
            if not self.in_app_enabled:
                return False
            if category == 'marketing' and not self.in_app_marketing:
                return False
            if category == 'event' and not self.in_app_event_updates:
                return False
            if category == 'order' and not self.in_app_order_updates:
                return False
        
        return True

    def is_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled or not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        from django.utils import timezone
        now = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day quiet hours (e.g., 22:00 to 08:00)
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Overnight quiet hours (e.g., 22:00 to 08:00)
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class NotificationLog(models.Model):
    """
    Log of notification delivery attempts and results
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_logs'
    )
    
    # Delivery attempt details
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices
    )
    
    # Provider details
    provider = models.CharField(max_length=100, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Error details
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    attempted_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-attempted_at']

    def __str__(self):
        return f"Log for {self.notification.title} - Attempt {self.attempt_number}"


class NotificationCampaign(models.Model):
    """
    Campaigns for bulk notifications
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Campaign details
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='campaigns'
    )
    
    # Targeting
    target_users = models.JSONField(default=list, blank=True, help_text='List of user IDs or criteria')
    target_criteria = models.JSONField(default=dict, blank=True, help_text='User filtering criteria')
    
    # Campaign status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('scheduled', 'Scheduled'),
            ('running', 'Running'),
            ('paused', 'Paused'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft'
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Statistics
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='created_campaigns'
    )

    class Meta:
        verbose_name = 'Notification Campaign'
        verbose_name_plural = 'Notification Campaigns'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.sent_count == 0:
            return 0.0
        return (self.delivered_count / self.sent_count) * 100

    @property
    def open_rate(self):
        """Calculate open rate percentage"""
        if self.delivered_count == 0:
            return 0.0
        return (self.opened_count / self.delivered_count) * 100

    @property
    def click_rate(self):
        """Calculate click rate percentage"""
        if self.delivered_count == 0:
            return 0.0
        return (self.clicked_count / self.delivered_count) * 100
