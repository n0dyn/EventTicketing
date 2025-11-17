from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Attendee, CheckIn, EventWaitlist, WaitlistEntry, WaitlistNotification, 
    WaitlistRelease, WaitlistPreference, TicketQRCode, CheckInLocation, 
    ScanSession, CheckInStats
)


@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    """
    Admin interface for Attendees
    """
    list_display = ('full_name', 'email', 'event', 'ticket_type_name', 'is_checked_in', 'check_in_time', 'created_at')
    list_filter = ('is_checked_in', 'event', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'event__title')
    readonly_fields = ('is_checked_in', 'check_in_time', 'checked_in_by', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Attendee Information', {
            'fields': ('event', 'user', 'ticket', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Additional Information', {
            'fields': ('company', 'job_title', 'dietary_requirements', 'special_needs'),
            'classes': ('collapse',)
        }),
        ('Check-in Status', {
            'fields': ('is_checked_in', 'check_in_time', 'checked_in_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'user', 'ticket', 'checked_in_by')


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    """
    Admin interface for Check-ins
    """
    list_display = ('user', 'event', 'status', 'check_in_time', 'check_out_time', 'scanner_user', 'scan_result')
    list_filter = ('status', 'scan_result', 'check_in_time', 'event')
    search_fields = ('user__email', 'event__title', 'ticket__ticket_code')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'check_in_time'
    
    fieldsets = (
        ('Check-in Information', {
            'fields': ('qr_code', 'ticket', 'event', 'user', 'status')
        }),
        ('Timing', {
            'fields': ('check_in_time', 'check_out_time')
        }),
        ('Location & Device', {
            'fields': ('check_in_location', 'scanner_device_id', 'scanner_user'),
            'classes': ('collapse',)
        }),
        ('Geolocation', {
            'fields': ('latitude', 'longitude', 'accuracy'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('scan_result', 'validation_errors'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('notes', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event', 'ticket', 'scanner_user', 'qr_code')


@admin.register(EventWaitlist)
class EventWaitlistAdmin(admin.ModelAdmin):
    """
    Admin interface for Event Waitlists
    """
    list_display = ('event', 'is_enabled', 'current_position_count', 'total_entries', 'conversion_rate', 'created_at')
    list_filter = ('is_enabled', 'auto_notify', 'enable_priority_queue', 'created_at')
    search_fields = ('event__title',)
    readonly_fields = ('total_entries', 'active_entries', 'converted_entries', 'conversion_rate', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Waitlist Settings', {
            'fields': ('event', 'is_enabled', 'max_capacity', 'auto_notify', 'notification_window_hours')
        }),
        ('Priority Settings', {
            'fields': ('enable_priority_queue', 'vip_percentage'),
            'classes': ('collapse',)
        }),
        ('Notification Settings', {
            'fields': ('notification_template_id', 'custom_message'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_entries', 'active_entries', 'converted_entries', 'conversion_rate'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for Waitlist Entries
    """
    list_display = ('user', 'event', 'position', 'priority', 'status', 'requested_tickets', 'joined_at')
    list_filter = ('status', 'priority', 'joined_at', 'event')
    search_fields = ('user__email', 'event__title')
    readonly_fields = ('created_at', 'updated_at', 'is_active', 'is_expired', 'time_on_waitlist')
    date_hierarchy = 'joined_at'
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('waitlist', 'user', 'event', 'position', 'priority', 'priority_score')
        }),
        ('Status & Timing', {
            'fields': ('status', 'joined_at', 'notified_at', 'expires_at', 'converted_at')
        }),
        ('User Preferences', {
            'fields': ('requested_tickets', 'max_price', 'preferred_ticket_types'),
            'classes': ('collapse',)
        }),
        ('Notification Preferences', {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('source', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Properties', {
            'fields': ('is_active', 'is_expired', 'time_on_waitlist'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event', 'waitlist')


@admin.register(WaitlistNotification)
class WaitlistNotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Waitlist Notifications
    """
    list_display = ('user', 'waitlist', 'notification_type', 'delivery_status', 'sent_at', 'expires_at', 'response_action')
    list_filter = ('notification_type', 'delivery_status', 'response_action', 'sent_at')
    search_fields = ('user__email', 'waitlist__event__title', 'subject')
    readonly_fields = ('created_at', 'updated_at', 'is_expired', 'response_time')
    date_hierarchy = 'sent_at'
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('waitlist', 'entry', 'user', 'notification_type', 'subject', 'message')
        }),
        ('Tickets Available', {
            'fields': ('available_tickets', 'ticket_types', 'special_offer'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('sent_at', 'expires_at', 'is_expired')
        }),
        ('Response Tracking', {
            'fields': ('opened_at', 'clicked_at', 'responded_at', 'response_action', 'response_time'),
            'classes': ('collapse',)
        }),
        ('Delivery Status', {
            'fields': ('delivery_status', 'delivery_attempts', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event', 'waitlist', 'entry')


@admin.register(WaitlistRelease)
class WaitlistReleaseAdmin(admin.ModelAdmin):
    """
    Admin interface for Waitlist Releases
    """
    list_display = ('event', 'tickets_released', 'processing_method', 'notifications_sent', 'successful_conversions', 'conversion_rate', 'processed_at')
    list_filter = ('release_reason', 'processing_method', 'processed_at')
    search_fields = ('event__title', 'notes')
    readonly_fields = ('conversion_rate', 'created_at')
    date_hierarchy = 'processed_at'
    
    fieldsets = (
        ('Release Information', {
            'fields': ('event', 'waitlist', 'tickets_released', 'ticket_type', 'release_reason')
        }),
        ('Processing', {
            'fields': ('processed_at', 'processing_method', 'created_by')
        }),
        ('Results', {
            'fields': ('notifications_sent', 'successful_conversions', 'failed_notifications', 'conversion_rate')
        }),
        ('Priority Distribution', {
            'fields': ('vip_notifications', 'regular_notifications'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'metadata'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'waitlist', 'ticket_type', 'created_by')


@admin.register(WaitlistPreference)
class WaitlistPreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for Waitlist Preferences
    """
    list_display = ('user', 'default_email_notifications', 'default_sms_notifications', 'default_push_notifications', 'conversion_rate')
    list_filter = ('default_email_notifications', 'default_sms_notifications', 'default_push_notifications', 'priority_eligible')
    search_fields = ('user__email',)
    readonly_fields = ('conversion_rate', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Preferences', {
            'fields': ('email_enabled', 'email_marketing', 'email_event_updates', 'email_order_updates', 'email_waitlist_updates')
        }),
        ('SMS Preferences', {
            'fields': ('sms_enabled', 'sms_phone', 'sms_marketing', 'sms_event_reminders', 'sms_order_updates'),
            'classes': ('collapse',)
        }),
        ('Push Notification Preferences', {
            'fields': ('push_enabled', 'push_marketing', 'push_event_updates', 'push_order_updates', 'push_waitlist_updates'),
            'classes': ('collapse',)
        }),
        ('In-App Preferences', {
            'fields': ('in_app_enabled', 'in_app_marketing', 'in_app_event_updates', 'in_app_order_updates'),
            'classes': ('collapse',)
        }),
        ('Frequency & Timing', {
            'fields': ('digest_frequency', 'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end', 'quiet_hours_timezone'),
            'classes': ('collapse',)
        }),
        ('Priority Settings', {
            'fields': ('priority_eligible', 'priority_level', 'priority_expires_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_waitlist_joins', 'successful_conversions', 'average_wait_time_hours', 'conversion_rate'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(TicketQRCode)
class TicketQRCodeAdmin(admin.ModelAdmin):
    """
    Admin interface for Ticket QR Codes
    """
    list_display = ('ticket', 'event', 'access_level', 'is_active', 'current_usage', 'usage_limit', 'is_valid', 'generated_at')
    list_filter = ('is_active', 'access_level', 'generated_at')
    search_fields = ('ticket__ticket_code', 'event__title', 'qr_code_data')
    readonly_fields = ('qr_code_data', 'qr_code_hash', 'is_valid', 'can_be_used', 'generated_at')
    
    fieldsets = (
        ('QR Code Information', {
            'fields': ('ticket', 'order', 'event', 'qr_code_data', 'qr_code_hash')
        }),
        ('Security', {
            'fields': ('secret_key', 'validation_data'),
            'classes': ('collapse',)
        }),
        ('Access Control', {
            'fields': ('access_level', 'restricted_areas')
        }),
        ('Usage', {
            'fields': ('is_active', 'usage_limit', 'current_usage', 'is_valid', 'can_be_used')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until'),
            'classes': ('collapse',)
        }),
        ('Generation', {
            'fields': ('generated_at', 'generated_by', 'version'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ticket', 'order', 'event', 'generated_by')


@admin.register(CheckInLocation)
class CheckInLocationAdmin(admin.ModelAdmin):
    """
    Admin interface for Check-in Locations
    """
    list_display = ('name', 'event', 'location_type', 'required_access_level', 'is_active', 'is_open', 'is_at_capacity')
    list_filter = ('location_type', 'required_access_level', 'is_active', 'is_monitored', 'event')
    search_fields = ('name', 'description', 'event__title')
    readonly_fields = ('is_open', 'is_at_capacity', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Location Information', {
            'fields': ('event', 'name', 'description', 'location_type')
        }),
        ('Access Control', {
            'fields': ('required_access_level', 'allowed_ticket_types')
        }),
        ('Capacity & Flow', {
            'fields': ('max_capacity', 'current_occupancy', 'is_at_capacity')
        }),
        ('Timing', {
            'fields': ('opens_at', 'closes_at', 'is_open'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_monitored')
        }),
        ('Physical Location', {
            'fields': ('latitude', 'longitude', 'geofence_radius'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')


@admin.register(ScanSession)
class ScanSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for Scan Sessions
    """
    list_display = ('user', 'event', 'device_name', 'is_active', 'scans_performed', 'success_rate', 'started_at')
    list_filter = ('is_active', 'event', 'started_at')
    search_fields = ('user__email', 'device_name', 'device_id', 'event__title')
    readonly_fields = ('success_rate', 'created_at', 'updated_at')
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_token', 'device_id', 'device_name', 'user', 'event', 'location')
        }),
        ('Status', {
            'fields': ('is_active', 'started_at', 'last_activity', 'ended_at')
        }),
        ('Statistics', {
            'fields': ('scans_performed', 'successful_scans', 'failed_scans', 'success_rate')
        }),
        ('Device Information', {
            'fields': ('device_info', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event', 'location')


@admin.register(CheckInStats)
class CheckInStatsAdmin(admin.ModelAdmin):
    """
    Admin interface for Check-in Statistics
    """
    list_display = ('event', 'total_tickets', 'checked_in_count', 'currently_at_event', 'attendance_rate', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('event__title',)
    readonly_fields = ('attendance_rate', 'current_occupancy_rate', 'last_updated')
    
    fieldsets = (
        ('Event', {
            'fields': ('event',)
        }),
        ('Current Status', {
            'fields': ('total_tickets', 'checked_in_count', 'checked_out_count', 'currently_at_event')
        }),
        ('Peak Metrics', {
            'fields': ('peak_occupancy', 'peak_occupancy_time'),
            'classes': ('collapse',)
        }),
        ('Flow Metrics', {
            'fields': ('average_check_in_time', 'busiest_entrance', 'busiest_hour'),
            'classes': ('collapse',)
        }),
        ('Conversion Metrics', {
            'fields': ('no_show_count', 'late_arrival_count'),
            'classes': ('collapse',)
        }),
        ('Breakdowns', {
            'fields': ('hourly_check_ins', 'location_breakdown'),
            'classes': ('collapse',)
        }),
        ('Calculated Rates', {
            'fields': ('attendance_rate', 'current_occupancy_rate'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')
    
    def has_add_permission(self, request):
        return False  # Stats should be generated automatically
