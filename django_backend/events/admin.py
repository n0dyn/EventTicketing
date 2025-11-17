from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Event, EventCategory, EventSeries, RecurrencePattern, EventInstance


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Event Categories
    """
    list_display = ('name', 'color_display', 'description', 'event_count', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'event_count')
    
    def color_display(self, obj):
        """Display color as colored box"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block;"></div> {}',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'
    
    def event_count(self, obj):
        """Display number of events in this category"""
        count = obj.events.count()
        return format_html('<strong>{}</strong>', count)
    event_count.short_description = 'Events'


class TicketTypeInline(admin.TabularInline):
    """Inline admin for ticket types within event admin"""
    model = None  # Will be set when tickets app is registered
    extra = 1
    fields = ('name', 'price', 'quantity', 'sold_count', 'is_active')
    readonly_fields = ('sold_count',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    Admin interface for Events
    """
    list_display = ('title', 'organization', 'owner', 'start_datetime', 'status', 'is_public', 'capacity', 'ticket_count', 'created_at')
    list_filter = ('status', 'is_public', 'is_active', 'organization', 'categories', 'start_datetime')
    search_fields = ('title', 'description', 'location', 'venue')
    readonly_fields = ('created_at', 'updated_at', 'ticket_count', 'available_capacity', 'is_sold_out')
    date_hierarchy = 'start_datetime'
    filter_horizontal = ('categories',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'categories')
        }),
        ('Organization & Owner', {
            'fields': ('organization', 'owner')
        }),
        ('Date & Time', {
            'fields': ('start_datetime', 'end_datetime', 'event_timezone')
        }),
        ('Location', {
            'fields': ('location', 'venue')
        }),
        ('Images', {
            'fields': ('featured_image', 'banner_image')
        }),
        ('Pricing & Capacity', {
            'fields': ('price', 'currency', 'is_free', 'capacity')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_public', 'is_active')
        }),
        ('Recurring Events', {
            'fields': ('is_part_of_series', 'event_series'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('ticket_count', 'available_capacity', 'is_sold_out', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def ticket_count(self, obj):
        """Display total tickets sold"""
        count = obj.total_tickets_sold
        return format_html('<strong>{}</strong>', count)
    ticket_count.short_description = 'Tickets Sold'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'owner', 'event_series').prefetch_related('categories')


@admin.register(RecurrencePattern)
class RecurrencePatternAdmin(admin.ModelAdmin):
    """
    Admin interface for Recurrence Patterns
    """
    list_display = ('recurrence_type', 'interval_count', 'end_date', 'occurrence_count', 'created_at')
    list_filter = ('recurrence_type', 'created_at')
    search_fields = ('custom_rule',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Pattern Definition', {
            'fields': ('recurrence_type', 'interval_count')
        }),
        ('Weekly Settings', {
            'fields': ('weekdays',),
            'classes': ('collapse',)
        }),
        ('Monthly Settings', {
            'fields': ('month_day', 'month_week', 'month_weekday'),
            'classes': ('collapse',)
        }),
        ('Yearly Settings', {
            'fields': ('year_month', 'year_day'),
            'classes': ('collapse',)
        }),
        ('End Conditions', {
            'fields': ('end_date', 'occurrence_count')
        }),
        ('Advanced Options', {
            'fields': ('exclude_dates', 'include_dates', 'timezone', 'custom_rule'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EventSeries)
class EventSeriesAdmin(admin.ModelAdmin):
    """
    Admin interface for Event Series (Recurring Events)
    """
    list_display = ('title', 'organization', 'owner', 'recurrence_pattern', 'total_events', 'upcoming_events', 'is_active', 'created_at')
    list_filter = ('is_active', 'auto_publish', 'organization', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'total_events', 'upcoming_events')
    filter_horizontal = ()
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Organization & Owner', {
            'fields': ('organization', 'owner')
        }),
        ('Recurrence Settings', {
            'fields': ('recurrence_pattern', 'series_start_date', 'series_end_date')
        }),
        ('Time Settings', {
            'fields': ('default_start_time', 'default_end_time', 'default_duration_minutes'),
            'classes': ('collapse',)
        }),
        ('Template Data', {
            'fields': ('template_data',),
            'classes': ('collapse',)
        }),
        ('Generation Settings', {
            'fields': ('advance_days', 'max_instances', 'auto_publish'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Statistics', {
            'fields': ('total_events', 'upcoming_events', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'owner', 'recurrence_pattern')


@admin.register(EventInstance)
class EventInstanceAdmin(admin.ModelAdmin):
    """
    Admin interface for Event Instances (Customizations)
    """
    list_display = ('event', 'event_series', 'is_cancelled', 'custom_title', 'created_at')
    list_filter = ('is_cancelled', 'event_series', 'created_at')
    search_fields = ('event__title', 'custom_title', 'custom_description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Event Reference', {
            'fields': ('event', 'event_series')
        }),
        ('Custom Content', {
            'fields': ('custom_title', 'custom_description', 'custom_location')
        }),
        ('Custom Timing', {
            'fields': ('custom_start_datetime', 'custom_end_datetime'),
            'classes': ('collapse',)
        }),
        ('Status Modifications', {
            'fields': ('is_cancelled', 'cancellation_reason')
        }),
        ('Additional Data', {
            'fields': ('custom_data',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'event_series')
