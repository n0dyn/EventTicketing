"""
Event serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import Event, EventCategory, EventSeries, RecurrencePattern, EventInstance


class EventCategorySerializer(serializers.ModelSerializer):
    """Event category serializer"""
    event_count = serializers.ReadOnlyField()
    
    class Meta:
        model = EventCategory
        fields = [
            'id', 'name', 'description', 'color', 'icon',
            'is_active', 'created_at', 'updated_at', 'event_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'event_count']


class RecurrencePatternSerializer(serializers.ModelSerializer):
    """Recurrence pattern serializer"""
    
    class Meta:
        model = RecurrencePattern
        fields = [
            'id', 'recurrence_type', 'interval_count', 'weekdays',
            'month_day', 'month_week', 'month_weekday', 'year_month',
            'year_day', 'end_date', 'occurrence_count', 'exclude_dates',
            'include_dates', 'timezone_field', 'custom_rule'
        ]


class EventInstanceSerializer(serializers.ModelSerializer):
    """Event instance serializer for recurring events"""
    
    class Meta:
        model = EventInstance
        fields = [
            'id', 'event', 'event_series', 'custom_title', 'custom_description',
            'custom_location', 'custom_start_datetime', 'custom_end_datetime',
            'is_cancelled', 'cancellation_reason', 'custom_data'
        ]
        read_only_fields = ['id']


class EventSeriesSerializer(serializers.ModelSerializer):
    """Event series serializer"""
    recurrence_pattern = RecurrencePatternSerializer(read_only=True)
    total_events = serializers.ReadOnlyField()
    upcoming_events = serializers.ReadOnlyField()
    
    class Meta:
        model = EventSeries
        fields = [
            'id', 'name', 'description', 'recurrence_pattern',
            'series_start_date', 'series_end_date', 'default_start_time',
            'default_end_time', 'default_duration_minutes', 'is_active',
            'auto_publish', 'advance_days', 'max_instances',
            'owner', 'organization', 'created_at', 'updated_at',
            'total_events', 'upcoming_events'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_events', 'upcoming_events']


class EventSerializer(serializers.ModelSerializer):
    """Event serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    owner_name = serializers.CharField(source='owner.full_name', read_only=True)
    is_past = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    is_today = serializers.ReadOnlyField()
    days_until = serializers.ReadOnlyField()
    capacity_remaining = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    ticket_sales_total = serializers.ReadOnlyField()
    ticket_sales_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'description', 'categories',
            'organization', 'organization_name', 'owner', 'owner_name',
            'start_datetime', 'end_datetime', 'event_timezone', 'location',
            'venue', 'capacity', 'capacity_remaining', 'is_sold_out',
            'ticket_sales_total', 'ticket_sales_count', 'status', 'is_public',
            'is_active', 'is_past', 'is_upcoming', 'is_today', 'days_until',
            'banner_image', 'featured_image', 'price', 'currency', 'is_free',
            'is_part_of_series', 'event_series', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'created_at', 'updated_at', 'organization_name',
            'owner_name', 'is_past', 'is_upcoming', 'is_today', 'days_until',
            'capacity_remaining', 'is_sold_out', 'ticket_sales_total', 'ticket_sales_count'
        ]


class EventCreateSerializer(serializers.ModelSerializer):
    """Event creation serializer"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'categories', 'organization',
            'start_datetime', 'end_datetime', 'event_timezone', 'location',
            'venue', 'capacity', 'banner_image', 'featured_image',
            'price', 'currency', 'is_free', 'is_public', 'is_active'
        ]


class EventUpdateSerializer(serializers.ModelSerializer):
    """Event update serializer"""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'categories', 'start_datetime',
            'end_datetime', 'event_timezone', 'location', 'venue',
            'capacity', 'status', 'is_public', 'is_active',
            'banner_image', 'featured_image', 'price', 'currency', 'is_free'
        ]


class EventListSerializer(serializers.ModelSerializer):
    """Event list serializer (minimal fields)"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    is_past = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    capacity_remaining = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'organization', 'organization_name', 'start_datetime', 'end_datetime',
            'location', 'capacity', 'capacity_remaining', 'is_sold_out', 'status',
            'is_public', 'featured_image', 'is_past', 'is_upcoming', 'created_at'
        ]


class EventPublishSerializer(serializers.Serializer):
    """Event publish serializer"""
    publish = serializers.BooleanField()
    message = serializers.CharField(required=False, allow_blank=True)
