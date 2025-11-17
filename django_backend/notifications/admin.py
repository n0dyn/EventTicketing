from django.contrib import admin
from django.utils.html import format_html
from .models import (
    EmailTemplate, NotificationTemplate, Notification, NotificationPreference,
    NotificationLog, NotificationCampaign
)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for Email Templates
    """
    list_display = ('name', 'category', 'is_active', 'created_by', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'subject')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Variables', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification Templates
    """
    list_display = ('name', 'notification_type', 'category', 'priority', 'is_active', 'created_by', 'created_at')
    list_filter = ('notification_type', 'category', 'priority', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'title_template')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Notification Settings', {
            'fields': ('notification_type', 'title_template', 'message_template', 'email_template')
        }),
        ('Delivery Settings', {
            'fields': ('priority', 'retry_attempts', 'retry_delay_minutes')
        }),
        ('Variables', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by', 'email_template')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notifications
    """
    list_display = ('title', 'user', 'notification_type', 'status', 'priority', 'sent_at', 'delivered_at', 'created_at')
    list_filter = ('notification_type', 'status', 'priority', 'created_at', 'sent_at')
    search_fields = ('title', 'user__email', 'message')
    readonly_fields = ('id', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'should_retry', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('id', 'user', 'notification_type', 'title', 'message', 'template')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Delivery Tracking', {
            'fields': ('sent_at', 'delivered_at', 'opened_at', 'clicked_at')
        }),
        ('Retry Logic', {
            'fields': ('retry_count', 'max_retries', 'next_retry_at', 'should_retry'),
            'classes': ('collapse',)
        }),
        ('Error Handling', {
            'fields': ('error_message', 'error_code'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('data', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'template')
    
    def has_add_permission(self, request):
        return False  # Notifications should be created through the system


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification Preferences
    """
    list_display = ('user', 'email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled', 'digest_frequency', 'created_at')
    list_filter = ('email_enabled', 'sms_enabled', 'push_enabled', 'in_app_enabled', 'digest_frequency', 'quiet_hours_enabled')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    
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
        ('Statistics', {
            'fields': ('conversion_rate', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification Logs
    """
    list_display = ('notification', 'attempt_number', 'status', 'provider', 'attempted_at', 'completed_at')
    list_filter = ('status', 'provider', 'attempted_at')
    search_fields = ('notification__title', 'notification__user__email', 'provider_message_id')
    readonly_fields = ('id', 'attempted_at', 'completed_at')
    date_hierarchy = 'attempted_at'
    
    fieldsets = (
        ('Log Information', {
            'fields': ('id', 'notification', 'attempt_number', 'status')
        }),
        ('Provider Details', {
            'fields': ('provider', 'provider_message_id', 'provider_response'),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_message', 'error_code'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('attempted_at', 'completed_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification', 'notification__user')
    
    def has_add_permission(self, request):
        return False  # Logs should be created automatically


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification Campaigns
    """
    list_display = ('name', 'notification_type', 'status', 'total_recipients', 'sent_count', 'delivery_rate', 'open_rate', 'created_at')
    list_filter = ('notification_type', 'status', 'created_at', 'scheduled_at')
    search_fields = ('name', 'description', 'created_by__email')
    readonly_fields = ('delivery_rate', 'open_rate', 'click_rate', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description', 'notification_type', 'template')
        }),
        ('Targeting', {
            'fields': ('target_users', 'target_criteria'),
            'classes': ('collapse',)
        }),
        ('Status & Scheduling', {
            'fields': ('status', 'scheduled_at', 'started_at', 'completed_at')
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'sent_count', 'delivered_count', 'failed_count', 'opened_count', 'clicked_count')
        }),
        ('Performance Metrics', {
            'fields': ('delivery_rate', 'open_rate', 'click_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('template', 'created_by')
    
    def has_add_permission(self, request):
        return False  # Campaigns should be created through the system
