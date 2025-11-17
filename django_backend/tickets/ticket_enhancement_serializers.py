"""
Serializers for ticketing system enhancements
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .ticket_enhancements import (
    TicketDisablement, TicketBlacklist, UserBan,
    TicketTransfer, EventMetrics, LocationMetrics,
    TicketStatus, BanReason
)

User = get_user_model()


# ============================================================================
# TICKET DISABLEMENT SERIALIZERS
# ============================================================================

class TicketDisablementSerializer(serializers.ModelSerializer):
    """Serialize ticket disablement records"""
    disabled_by_user = serializers.SerializerMethodField()
    re_enabled_by_user = serializers.SerializerMethodField()
    ticket_code = serializers.CharField(source='ticket.ticket_code', read_only=True)
    
    class Meta:
        model = TicketDisablement
        fields = [
            'id', 'ticket', 'ticket_code', 'status', 'reason',
            'detailed_reason', 'disabled_by', 'disabled_by_user',
            'disabled_at', 're_enabled_at', 're_enabled_by',
            're_enabled_by_user', 'evidence_data', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']
    
    def get_disabled_by_user(self, obj):
        if obj.disabled_by:
            return {
                'id': obj.disabled_by.id,
                'email': obj.disabled_by.email,
                'full_name': obj.disabled_by.full_name
            }
        return None
    
    def get_re_enabled_by_user(self, obj):
        if obj.re_enabled_by:
            return {
                'id': obj.re_enabled_by.id,
                'email': obj.re_enabled_by.email,
                'full_name': obj.re_enabled_by.full_name
            }
        return None


class TicketBlacklistSerializer(serializers.ModelSerializer):
    """Serialize ticket blacklist entries"""
    ticket_code = serializers.CharField(source='ticket.ticket_code', read_only=True)
    blacklisted_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketBlacklist
        fields = [
            'id', 'event', 'ticket', 'ticket_code',
            'ticket_code_pattern', 'reason', 'severity',
            'blacklisted_at', 'blacklisted_by',
            'blacklisted_by_user', 'expires_at',
            'evidence', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'blacklisted_at', 'is_active']
    
    def get_blacklisted_by_user(self, obj):
        if obj.blacklisted_by:
            return {
                'id': obj.blacklisted_by.id,
                'email': obj.blacklisted_by.email
            }
        return None


# ============================================================================
# USER BAN SERIALIZERS
# ============================================================================

class UserBanSerializer(serializers.ModelSerializer):
    """Serialize user ban records"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, required=False)
    issued_by_user = serializers.SerializerMethodField()
    appeal_reviewed_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = UserBan
        fields = [
            'id', 'user', 'user_email', 'user_full_name',
            'event', 'event_title', 'reason', 'description',
            'evidence', 'ban_issued_at', 'ban_until',
            'issued_by', 'issued_by_user', 'days_remaining',
            'is_permanent', 'is_active', 'appeal_requested_at',
            'appeal_notes', 'appeal_reviewed_at', 'appeal_approved',
            'appeal_reviewed_by', 'appeal_reviewed_by_user',
            'lifted_at', 'lifted_by', 'lift_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'is_active',
            'is_permanent', 'days_remaining', 'ban_issued_at'
        ]
    
    def get_issued_by_user(self, obj):
        if obj.issued_by:
            return {
                'id': obj.issued_by.id,
                'email': obj.issued_by.email
            }
        return None
    
    def get_appeal_reviewed_by_user(self, obj):
        if obj.appeal_reviewed_by:
            return {
                'id': obj.appeal_reviewed_by.id,
                'email': obj.appeal_reviewed_by.email
            }
        return None


class UserBanCreateSerializer(serializers.ModelSerializer):
    """Create a new user ban"""
    
    class Meta:
        model = UserBan
        fields = [
            'user', 'event', 'reason', 'description',
            'evidence', 'ban_until'
        ]
    
    def create(self, validated_data):
        # Set issued_by to current user
        request = self.context.get('request')
        if request and request.user:
            validated_data['issued_by'] = request.user
        
        return super().create(validated_data)


# ============================================================================
# TICKET TRANSFER SERIALIZERS
# ============================================================================

class TicketTransferSerializer(serializers.ModelSerializer):
    """Serialize ticket transfers"""
    from_user_email = serializers.CharField(source='from_user.email', read_only=True)
    to_user_email = serializers.CharField(source='to_user.email', read_only=True)
    ticket_code = serializers.CharField(source='ticket.ticket_code', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    platform_fee_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = TicketTransfer
        fields = [
            'id', 'ticket', 'ticket_code', 'from_user',
            'from_user_email', 'to_user', 'to_user_email',
            'transfer_type', 'original_price', 'resale_price',
            'platform_fee_percent', 'platform_fee_amount',
            'status', 'requested_at', 'expires_at',
            'accepted_at', 'completed_at', 'regenerate_qr',
            'is_expired', 'transfer_notes', 'decline_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'from_user', 'requested_at',
            'accepted_at', 'completed_at', 'created_at',
            'updated_at', 'is_expired'
        ]
    
    def get_platform_fee_amount(self, obj):
        if obj.resale_price and obj.platform_fee_percent:
            return float(obj.resale_price) * (obj.platform_fee_percent / 100)
        return None


class TicketTransferCreateSerializer(serializers.ModelSerializer):
    """Create a new ticket transfer"""
    
    class Meta:
        model = TicketTransfer
        fields = [
            'ticket', 'to_user', 'transfer_type',
            'resale_price', 'transfer_notes'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['from_user'] = request.user
        
        # Calculate expiration (48 hours for pending)
        validated_data['expires_at'] = timezone.now() + timezone.timedelta(hours=48)
        
        # Set original price if gift
        if validated_data['transfer_type'] == 'gift':
            validated_data['original_price'] = validated_data['ticket'].ticket_type.price
        
        return super().create(validated_data)


# ============================================================================
# METRICS SERIALIZERS
# ============================================================================

class EventMetricsSerializer(serializers.ModelSerializer):
    """Serialize event metrics"""
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = EventMetrics
        fields = [
            'id', 'event', 'event_title',
            # Revenue
            'total_revenue', 'revenue_by_ticket_type',
            'refund_total', 'avg_ticket_price',
            # Attendance
            'total_purchased', 'total_attended',
            'no_show_rate', 'no_show_count',
            'late_arrival_count', 'late_arrival_percentage',
            # Conversion
            'registration_to_purchase_rate',
            'waitlist_to_purchase_rate',
            'promo_code_usage_rate',
            'payment_failure_rate',
            # Fraud
            'suspicious_transactions',
            'duplicate_ticket_attempts',
            'refund_rate',
            'banned_user_entry_attempts',
            # Demographics
            'age_distribution', 'geographic_distribution',
            'repeat_attendee_rate',
            # Traffic
            'peak_entry_time', 'peak_exit_time',
            'avg_session_duration', 'busiest_day_of_week',
            'last_updated'
        ]
        read_only_fields = fields


class LocationMetricsSerializer(serializers.ModelSerializer):
    """Serialize location metrics"""
    location_name = serializers.CharField(source='location.name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    
    class Meta:
        model = LocationMetrics
        fields = [
            'id', 'location', 'location_name', 'event',
            'event_title', 'date', 'hour',
            'total_entries', 'total_exits',
            'peak_flow_time', 'avg_processing_time',
            'entries_by_ticket_type', 'entries_by_access_level',
            'success_rate', 'error_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

