from django.db import models
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import uuid


class EventStatus(models.TextChoices):
    """Choices for event status"""
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class EventCategory(models.Model):
    """
    Model for event categories
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Category'
        verbose_name_plural = 'Event Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    """
    Model for events
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(blank=True)
    
    # Location details
    location = models.CharField(max_length=255, blank=True)
    venue = models.CharField(max_length=255, blank=True)
    
    # Date and time
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    event_timezone = models.CharField(max_length=50, default='UTC')
    
    # Images
    featured_image = models.ImageField(upload_to='events/images/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    
    # Event details
    capacity = models.PositiveIntegerField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    is_free = models.BooleanField(default=False)
    
    # Status and visibility
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT
    )
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    # Recurring event support
    is_part_of_series = models.BooleanField(default=False)
    event_series = models.ForeignKey(
        'EventSeries',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='events'
    )
    
    # Relationships
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_events'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='events'
    )
    categories = models.ManyToManyField(
        EventCategory,
        blank=True,
        related_name='events'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        ordering = ['-start_datetime']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('events:detail', kwargs={'slug': self.slug})

    @property
    def start_date(self):
        """Get the date portion of start_datetime"""
        return self.start_datetime.date()

    @property
    def is_recurring(self):
        """Check if this event is part of a recurring series"""
        return self.is_part_of_series and self.event_series is not None
    
    @property
    def is_past(self):
        """Check if event is in the past"""
        return self.end_datetime < timezone.now()
    
    @property
    def is_upcoming(self):
        """Check if event is in the future"""
        return self.start_datetime > timezone.now()
    
    @property
    def is_today(self):
        """Check if event is today"""
        today = timezone.now().date()
        return self.start_datetime.date() == today
    
    @property
    def days_until(self):
        """Days until event starts"""
        if self.is_past:
            return 0
        delta = self.start_datetime.date() - timezone.now().date()
        return delta.days

    @property
    def total_tickets_sold(self):
        """Return total number of tickets sold"""
        return sum(ticket_type.sold_count for ticket_type in self.ticket_types.all())

    @property
    def available_capacity(self):
        """Return remaining capacity"""
        if self.capacity:
            return max(0, self.capacity - self.total_tickets_sold)
        return None
    
    @property
    def capacity_remaining(self):
        """Return remaining capacity (alias for available_capacity)"""
        return self.available_capacity
    
    @property
    def ticket_sales_total(self):
        """Return total revenue from ticket sales"""
        # This would need to be implemented based on actual ticket sales
        return 0
    
    @property
    def ticket_sales_count(self):
        """Return total number of tickets sold"""
        return self.total_tickets_sold

    @property
    def is_sold_out(self):
        """Check if event is sold out"""
        if self.capacity:
            return self.total_tickets_sold >= self.capacity
        return False


class RecurrenceType(models.TextChoices):
    """Types of recurrence patterns"""
    NONE = 'none', 'None'
    DAILY = 'daily', 'Daily'
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'
    YEARLY = 'yearly', 'Yearly'
    CUSTOM = 'custom', 'Custom'


class RecurrencePattern(models.Model):
    """
    Defines the recurrence pattern for events
    Supports complex scheduling rules
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Pattern definition
    recurrence_type = models.CharField(
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.WEEKLY
    )
    interval_count = models.PositiveIntegerField(default=1, help_text='Every N days/weeks/months')
    
    # Weekly recurrence - days of week (0=Monday, 6=Sunday)
    weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text='[0, 1, 2, 3, 4] for weekdays'
    )
    
    # Monthly recurrence options
    month_day = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Day of month (1-31)'
    )
    month_week = models.IntegerField(
        blank=True,
        null=True,
        help_text='Week of month (1-4, -1=last)'
    )
    month_weekday = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Day of week (0-6)'
    )
    
    # Yearly recurrence
    year_month = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Month of year (1-12)'
    )
    year_day = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Day of month'
    )
    
    # End conditions
    end_date = models.DateField(blank=True, null=True, help_text='End by date')
    occurrence_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='End after N occurrences'
    )
    
    # Advanced options
    exclude_dates = models.JSONField(
        default=list,
        blank=True,
        help_text='List of dates to skip'
    )
    include_dates = models.JSONField(
        default=list,
        blank=True,
        help_text='Additional specific dates'
    )
    timezone_field = models.CharField(max_length=50, default='UTC')
    
    # Custom rule (for complex patterns)
    custom_rule = models.TextField(blank=True, help_text='RRULE format or custom expression')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recurrence Pattern'
        verbose_name_plural = 'Recurrence Patterns'

    def __str__(self):
        return f"{self.get_recurrence_type_display()} (every {self.interval_count})"

    def generate_dates(self, start_date, end_date=None, limit=100):
        """
        Generate list of dates based on recurrence pattern
        """
        from datetime import date, timedelta
        
        dates = []
        current_date = start_date
        count = 0
        
        # Use end_date from pattern if not provided
        if end_date is None and self.end_date:
            end_date = self.end_date
        
        # Use occurrence_count if no end_date
        max_count = self.occurrence_count or limit
        
        while count < max_count:
            if end_date and current_date > end_date:
                break
                
            # Check if date should be included
            if self._should_include_date(current_date):
                dates.append(current_date)
                count += 1
            
            # Move to next potential date
            current_date = self._next_date(current_date)
            
            # Safety check to prevent infinite loops
            if count > 1000:
                break
                
        return dates
    
    def _should_include_date(self, check_date):
        """Check if a date matches the recurrence pattern"""
        
        # Check exclude_dates
        if self.exclude_dates and check_date.isoformat() in self.exclude_dates:
            return False
        
        # Check include_dates (overrides pattern)
        if self.include_dates and check_date.isoformat() in self.include_dates:
            return True
        
        if self.recurrence_type == RecurrenceType.DAILY:
            return True
        
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            if self.weekdays:
                return check_date.weekday() in self.weekdays
            return True
        
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            if self.month_day:
                return check_date.day == self.month_day
            elif self.month_week is not None and self.month_weekday is not None:
                return self._matches_monthly_pattern(check_date)
            return True
        
        elif self.recurrence_type == RecurrenceType.YEARLY:
            matches = True
            if self.year_month:
                matches = matches and check_date.month == self.year_month
            if self.year_day:
                matches = matches and check_date.day == self.year_day
            return matches
        
        return True
    
    def _matches_monthly_pattern(self, check_date):
        """Check if date matches monthly week/weekday pattern"""
        if check_date.weekday() != self.month_weekday:
            return False
        
        # Calculate which week of the month this is
        week_of_month = ((check_date.day - 1) // 7) + 1
        
        # Handle "last week" case (-1)
        if self.month_week == -1:
            # Check if this is the last occurrence of this weekday in the month
            next_week = check_date + timedelta(days=7)
            return next_week.month != check_date.month
        
        return week_of_month == self.month_week
    
    def _next_date(self, current_date):
        """Calculate the next date to check based on recurrence type"""
        from datetime import timedelta
        
        if self.recurrence_type == RecurrenceType.DAILY:
            return current_date + timedelta(days=self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return current_date + timedelta(weeks=self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            # Add months (approximate with 30 days, will be corrected)
            return current_date + timedelta(days=30 * self.interval_count)
        
        elif self.recurrence_type == RecurrenceType.YEARLY:
            # Add years (approximate with 365 days, will be corrected)
            return current_date + timedelta(days=365 * self.interval_count)
        
        else:
            return current_date + timedelta(days=1)


class EventSeries(models.Model):
    """
    Represents a series of recurring events
    Acts as a parent for multiple event instances
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Series metadata
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    
    # Template for all events in series
    template_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Common event properties'
    )
    
    # Recurrence settings
    recurrence_pattern = models.ForeignKey(
        RecurrencePattern,
        on_delete=models.CASCADE,
        related_name='event_series'
    )
    
    # Series dates
    series_start_date = models.DateField()
    series_end_date = models.DateField(blank=True, null=True)
    
    # Time settings (applied to all events)
    default_start_time = models.TimeField(blank=True, null=True)
    default_end_time = models.TimeField(blank=True, null=True)
    default_duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    
    # Series status
    is_active = models.BooleanField(default=True)
    auto_publish = models.BooleanField(default=False, help_text='Auto-publish new instances')
    
    # Generation settings
    advance_days = models.PositiveIntegerField(default=30, help_text='Generate events N days in advance')
    max_instances = models.PositiveIntegerField(default=100, help_text='Max events to generate')
    
    # Ownership and metadata
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='event_series'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='event_series'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Series'
        verbose_name_plural = 'Event Series'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_events(self):
        """Count of generated events"""
        return self.events.count()
    
    @property
    def upcoming_events(self):
        """Count of future events"""
        from datetime import date
        now = date.today()
        return self.events.filter(start_datetime__date__gte=now).count()

    def generate_events(self, days_ahead=None):
        """
        Generate event instances based on recurrence pattern
        """
        from datetime import date, timedelta, datetime
        
        if not self.is_active:
            return []
        
        days_ahead = days_ahead or self.advance_days
        end_date = date.today() + timedelta(days=days_ahead)
        
        # Get dates from recurrence pattern
        dates = self.recurrence_pattern.generate_dates(
            start_date=self.series_start_date,
            end_date=min(end_date, self.series_end_date) if self.series_end_date else end_date,
            limit=self.max_instances
        )
        
        # Check which events already exist
        existing_dates = set(self.events.values_list('start_datetime__date', flat=True))
        new_dates = [d for d in dates if d not in existing_dates]
        
        new_events = []
        for event_date in new_dates:
            event_data = self._prepare_event_data(event_date)
            
            # Create the event
            event = Event.objects.create(**event_data)
            new_events.append(event)
        
        return new_events
    
    def _prepare_event_data(self, event_date):
        """Prepare event data for a specific date"""
        from datetime import datetime, timedelta
        
        # Start with template data
        event_data = self.template_data.copy() if self.template_data else {}
        
        # Override with series-specific data
        event_data.update({
            'title': self.title,
            'description': self.description,
            'start_datetime': datetime.combine(event_date, self.default_start_time or datetime.min.time()),
            'owner': self.owner,
            'organization': self.organization,
            'is_part_of_series': True,
            'event_series': self,
        })
        
        # Set times
        if self.default_start_time:
            start_datetime = datetime.combine(event_date, self.default_start_time)
            event_data['start_datetime'] = start_datetime
        
        if self.default_end_time:
            end_datetime = datetime.combine(event_date, self.default_end_time)
            event_data['end_datetime'] = end_datetime
        elif self.default_duration_minutes:
            start_datetime = event_data.get('start_datetime')
            if start_datetime:
                end_datetime = start_datetime + timedelta(minutes=self.default_duration_minutes)
                event_data['end_datetime'] = end_datetime
        
        # Set status based on auto_publish
        if self.auto_publish:
            event_data['status'] = EventStatus.PUBLISHED
        
        return event_data


class EventInstance(models.Model):
    """
    Individual modifications to recurring event instances
    Allows customization of specific occurrences
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reference to the main event
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name='event_instance'
    )
    event_series = models.ForeignKey(
        EventSeries,
        on_delete=models.CASCADE,
        related_name='event_instances'
    )
    
    # Instance-specific modifications
    custom_title = models.CharField(max_length=255, blank=True)
    custom_description = models.TextField(blank=True)
    custom_location = models.CharField(max_length=255, blank=True)
    
    # Time modifications
    custom_start_datetime = models.DateTimeField(blank=True, null=True)
    custom_end_datetime = models.DateTimeField(blank=True, null=True)
    
    # Status modifications
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    
    # Other modifications
    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Any other custom properties'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Event Instance'
        verbose_name_plural = 'Event Instances'

    def __str__(self):
        return f"Instance: {self.event.title}"

    @property
    def effective_title(self):
        """Get the effective title (custom or original)"""
        return self.custom_title or self.event.title

    @property
    def effective_description(self):
        """Get the effective description (custom or original)"""
        return self.custom_description or self.event.description

    @property
    def effective_location(self):
        """Get the effective location (custom or original)"""
        return self.custom_location or self.event.location

    @property
    def effective_start_datetime(self):
        """Get the effective start time (custom or original)"""
        return self.custom_start_datetime or self.event.start_datetime

    @property
    def effective_end_datetime(self):
        """Get the effective end time (custom or original)"""
        return self.custom_end_datetime or self.event.end_datetime
