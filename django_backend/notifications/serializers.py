"""
Notification serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import (
    EmailTemplate, NotificationTemplate, Notification,
    NotificationPreference, NotificationCampaign
)


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Email template serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'slug', 'organization', 'organization_name', 'subject',
            'html_content', 'text_content', 'variables', 'from_email', 'from_name',
            'reply_to', 'is_default', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'organization_name']


class EmailTemplateCreateSerializer(serializers.ModelSerializer):
    """Email template creation serializer"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'organization', 'subject', 'html_content', 'text_content',
            'variables', 'from_email', 'from_name', 'reply_to', 'is_default'
        ]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Notification template serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    email_template_name = serializers.CharField(source='email_template.name', read_only=True, allow_null=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'slug', 'organization', 'organization_name', 'email_template',
            'email_template_name', 'template_type', 'trigger_event', 'is_active',
            'notification_channels', 'send_delay_minutes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'organization_name', 'email_template_name']


class NotificationTemplateCreateSerializer(serializers.ModelSerializer):
    """Notification template creation serializer"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'organization', 'email_template', 'template_type',
            'trigger_event', 'notification_channels', 'send_delay_minutes'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer"""
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True, allow_null=True)
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'template', 'template_name',
            'subject', 'body', 'channel', 'status', 'status_display', 'sent_at',
            'read_at', 'error_message', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sent_at', 'read_at', 'created_at', 'updated_at',
            'recipient_name', 'template_name', 'status_display'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """Notification list serializer (minimal fields)"""
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_name', 'subject', 'channel', 'status',
            'status_display', 'read_at', 'created_at'
        ]


class NotificationSendSerializer(serializers.Serializer):
    """Send notification serializer"""
    recipient_ids = serializers.ListField(child=serializers.UUIDField())
    subject = serializers.CharField()
    body = serializers.CharField()
    channel = serializers.CharField(default='email')
    template_id = serializers.UUIDField(required=False, allow_null=True)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Notification preference serializer"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_name', 'order_confirmation', 'ticket_delivery',
            'event_reminders', 'promotional_emails', 'event_updates',
            'refund_notifications', 'system_notifications', 'prefer_unsubscribe',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_name', 'created_at', 'updated_at']


class NotificationPreferenceUpdateSerializer(serializers.ModelSerializer):
    """Notification preference update serializer"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'order_confirmation', 'ticket_delivery', 'event_reminders',
            'promotional_emails', 'event_updates', 'refund_notifications',
            'system_notifications', 'prefer_unsubscribe'
        ]


class NotificationCampaignSerializer(serializers.ModelSerializer):
    """Notification campaign serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    event_title = serializers.CharField(source='event.title', read_only=True, allow_null=True)
    sent_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = NotificationCampaign
        fields = [
            'id', 'name', 'organization', 'organization_name', 'event', 'event_title',
            'subject', 'message', 'channel', 'recipient_filter', 'sent_count',
            'failed_count', 'status', 'status_display', 'scheduled_at', 'sent_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sent_count', 'failed_count', 'organization_name', 'event_title',
            'status_display', 'created_at', 'updated_at'
        ]
    
    def get_sent_count(self, obj):
        """Count sent notifications"""
        return obj.notifications.filter(status='sent').count()
    
    def get_failed_count(self, obj):
        """Count failed notifications"""
        return obj.notifications.filter(status='failed').count()


class NotificationCampaignCreateSerializer(serializers.ModelSerializer):
    """Notification campaign creation serializer"""
    
    class Meta:
        model = NotificationCampaign
        fields = [
            'name', 'organization', 'event', 'subject', 'message',
            'channel', 'recipient_filter', 'scheduled_at'
        ]


class NotificationCampaignLaunchSerializer(serializers.Serializer):
    """Launch notification campaign serializer"""
    send_immediately = serializers.BooleanField(default=True)
    test_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False
    )


class BulkNotificationSerializer(serializers.Serializer):
    """Bulk send notifications serializer"""
    recipient_ids = serializers.ListField(child=serializers.UUIDField(), max_length=10000)
    subject = serializers.CharField()
    message = serializers.CharField()
    channel = serializers.CharField()
    template_id = serializers.UUIDField(required=False, allow_null=True)


class NotificationStatsSerializer(serializers.Serializer):
    """Notification statistics serializer"""
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_send_time = serializers.FloatField()
    channel_breakdown = serializers.JSONField()

