"""
Attendee serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import (
    Attendee, EventWaitlist, WaitlistEntry, WaitlistNotification,
    CheckIn, TicketQRCode
)


class TicketQRCodeSerializer(serializers.ModelSerializer):
    """Ticket QR code serializer"""
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    event_title = serializers.CharField(source='ticket.ticket_type.event.title', read_only=True)
    
    class Meta:
        model = TicketQRCode
        fields = [
            'id', 'ticket', 'ticket_number', 'event_title', 'qr_code_value',
            'is_used', 'used_at', 'valid_until', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'qr_code_value', 'used_at', 'created_at', 'updated_at']


class CheckInSerializer(serializers.ModelSerializer):
    """Check-in serializer"""
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    attendee_name = serializers.CharField(source='attendee.name', read_only=True)
    event_title = serializers.CharField(source='ticket.ticket_type.event.title', read_only=True)
    checked_in_by_name = serializers.CharField(source='checked_in_by.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = CheckIn
        fields = [
            'id', 'ticket', 'ticket_number', 'attendee', 'attendee_name',
            'event_title', 'checked_in_by', 'checked_in_by_name', 'checked_in_at',
            'check_in_method', 'check_in_location', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'checked_in_at', 'created_at', 'ticket_number', 'attendee_name', 'event_title', 'checked_in_by_name']


class CheckInListSerializer(serializers.ModelSerializer):
    """Check-in list serializer (minimal fields)"""
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    attendee_name = serializers.CharField(source='attendee.name', read_only=True)
    event_title = serializers.CharField(source='ticket.ticket_type.event.title', read_only=True)
    
    class Meta:
        model = CheckIn
        fields = [
            'id', 'ticket_number', 'attendee_name', 'event_title',
            'checked_in_at', 'check_in_method'
        ]


class AttendeeSerializer(serializers.ModelSerializer):
    """Attendee serializer"""
    event_title = serializers.CharField(source='event.title', read_only=True, allow_null=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Attendee
        fields = [
            'id', 'user', 'user_name', 'event', 'event_title', 'name', 'email',
            'phone', 'date_of_birth', 'address', 'city', 'state', 'country',
            'postal_code', 'company', 'dietary_restrictions', 'accessibility_needs',
            'custom_questions', 'attended', 'feedback', 'notes', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'event_title', 'user_name']


class AttendeeListSerializer(serializers.ModelSerializer):
    """Attendee list serializer (minimal fields)"""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Attendee
        fields = [
            'id', 'name', 'user_name', 'email', 'phone', 'attended', 'created_at'
        ]


class AttendeeCreateSerializer(serializers.ModelSerializer):
    """Attendee creation serializer"""
    
    class Meta:
        model = Attendee
        fields = [
            'event', 'name', 'email', 'phone', 'date_of_birth',
            'address', 'city', 'state', 'country', 'postal_code',
            'company', 'dietary_restrictions', 'accessibility_needs',
            'custom_questions', 'notes'
        ]


class AttendeeUpdateSerializer(serializers.ModelSerializer):
    """Attendee update serializer"""
    
    class Meta:
        model = Attendee
        fields = [
            'name', 'email', 'phone', 'date_of_birth', 'address',
            'city', 'state', 'country', 'postal_code', 'company',
            'dietary_restrictions', 'accessibility_needs', 'custom_questions',
            'attended', 'feedback', 'notes'
        ]


class WaitlistEntrySerializer(serializers.ModelSerializer):
    """Waitlist entry serializer"""
    attendee_name = serializers.CharField(source='attendee.name', read_only=True)
    attendee_email = serializers.CharField(source='attendee.email', read_only=True)
    position_display = serializers.SerializerMethodField()
    
    class Meta:
        model = WaitlistEntry
        fields = [
            'id', 'waitlist', 'attendee', 'attendee_name', 'attendee_email',
            'position', 'position_display', 'notified', 'notified_at',
            'priority_score', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'position', 'position_display', 'notified_at', 'created_at', 'updated_at']
    
    def get_position_display(self, obj):
        """Get human-readable position"""
        if obj.position == 1:
            return "1st in line"
        elif obj.position == 2:
            return "2nd in line"
        elif obj.position == 3:
            return "3rd in line"
        else:
            return f"{obj.position}th in line"


class WaitlistNotificationSerializer(serializers.ModelSerializer):
    """Waitlist notification serializer"""
    entry_position = serializers.IntegerField(source='entry.position', read_only=True)
    attendee_name = serializers.CharField(source='entry.attendee.name', read_only=True)
    
    class Meta:
        model = WaitlistNotification
        fields = [
            'id', 'entry', 'attendee_name', 'entry_position', 'notification_type',
            'sent_at', 'status', 'message', 'created_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at', 'entry_position', 'attendee_name']


class EventWaitlistSerializer(serializers.ModelSerializer):
    """Event waitlist serializer"""
    event_title = serializers.CharField(source='event.title', read_only=True)
    entry_count = serializers.SerializerMethodField()
    notified_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EventWaitlist
        fields = [
            'id', 'event', 'event_title', 'is_active', 'max_entries',
            'entry_count', 'notified_count', 'auto_notify', 'notification_template',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'event_title', 'entry_count', 'notified_count', 'created_at', 'updated_at']
    
    def get_entry_count(self, obj):
        """Count total waitlist entries"""
        return obj.entries.count()
    
    def get_notified_count(self, obj):
        """Count notified entries"""
        return obj.entries.filter(notified=True).count()


class EventWaitlistDetailSerializer(serializers.ModelSerializer):
    """Event waitlist detail serializer with entries"""
    event_title = serializers.CharField(source='event.title', read_only=True)
    entries = WaitlistEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = EventWaitlist
        fields = [
            'id', 'event', 'event_title', 'is_active', 'max_entries',
            'auto_notify', 'notification_template', 'entries', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class WaitlistJoinSerializer(serializers.Serializer):
    """Join waitlist serializer"""
    event_id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(required=False)


class BulkCheckInSerializer(serializers.Serializer):
    """Bulk check-in serializer"""
    ticket_ids = serializers.ListField(child=serializers.UUIDField())
    check_in_location = serializers.CharField(required=False)
    check_in_method = serializers.CharField(default='manual')
    
    def validate_ticket_ids(self, value):
        """Validate at least one ticket"""
        if not value:
            raise serializers.ValidationError("At least one ticket ID is required")
        if len(value) > 1000:
            raise serializers.ValidationError("Maximum 1000 tickets per operation")
        return value


class WaitlistNotifySerializer(serializers.Serializer):
    """Notify from waitlist serializer"""
    waitlist_entry_ids = serializers.ListField(child=serializers.UUIDField())
    ticket_availability = serializers.IntegerField(min_value=1)
    notification_message = serializers.CharField(required=False)

