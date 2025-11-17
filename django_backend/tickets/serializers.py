"""
Ticket serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import Ticket, TicketType, PriceTier, PromoCode


class PriceTierSerializer(serializers.ModelSerializer):
    """Price tier serializer"""
    
    class Meta:
        model = PriceTier
        fields = [
            'id', 'ticket_type', 'tier_name', 'price', 'quantity_available',
            'quantity_sold', 'start_date', 'end_date', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'quantity_sold', 'created_at', 'updated_at']


class PromoCodeSerializer(serializers.ModelSerializer):
    """Promo code serializer"""
    usage_count = serializers.ReadOnlyField()
    remaining_uses = serializers.ReadOnlyField()
    
    class Meta:
        model = PromoCode
        fields = [
            'id', 'code', 'discount_type', 'discount_value', 'description',
            'organization', 'event', 'ticket_types', 'start_date', 'end_date',
            'max_uses', 'usage_count', 'remaining_uses', 'min_purchase_amount',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'remaining_uses', 'created_at', 'updated_at']
    
    def validate_code(self, value):
        """Validate promo code format"""
        if len(value) < 3:
            raise serializers.ValidationError("Promo code must be at least 3 characters")
        if not value.isupper():
            raise serializers.ValidationError("Promo code must be uppercase")
        return value


class TicketTypeSerializer(serializers.ModelSerializer):
    """Ticket type serializer"""
    price_tiers = PriceTierSerializer(many=True, read_only=True)
    promo_codes = PromoCodeSerializer(many=True, read_only=True)
    available_quantity = serializers.ReadOnlyField()
    sold_quantity = serializers.ReadOnlyField()
    sales_total = serializers.ReadOnlyField()
    
    class Meta:
        model = TicketType
        fields = [
            'id', 'event', 'name', 'description', 'ticket_type', 'base_price',
            'currency', 'quantity_available', 'available_quantity', 'sold_quantity',
            'sales_total', 'include_fee', 'service_charge', 'is_active',
            'price_tiers', 'promo_codes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'available_quantity', 'sold_quantity', 'sales_total',
            'created_at', 'updated_at'
        ]
    
    def validate_quantity_available(self, value):
        """Validate quantity is positive"""
        if value < 0:
            raise serializers.ValidationError("Quantity must be positive")
        return value


class TicketTypeCreateSerializer(serializers.ModelSerializer):
    """Ticket type creation serializer"""
    
    class Meta:
        model = TicketType
        fields = [
            'event', 'name', 'description', 'ticket_type', 'base_price',
            'currency', 'quantity_available', 'include_fee', 'service_charge', 'is_active'
        ]


class TicketTypeUpdateSerializer(serializers.ModelSerializer):
    """Ticket type update serializer"""
    
    class Meta:
        model = TicketType
        fields = [
            'name', 'description', 'base_price', 'currency',
            'quantity_available', 'include_fee', 'service_charge', 'is_active'
        ]


class TicketSerializer(serializers.ModelSerializer):
    """Ticket serializer"""
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    event_title = serializers.CharField(source='ticket_type.event.title', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True, allow_null=True)
    attendee_name = serializers.CharField(source='attendee.name', read_only=True, allow_null=True)
    qr_code_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_type', 'ticket_type_name', 'event_title', 'order', 'order_number',
            'attendee', 'attendee_name', 'ticket_number', 'status', 'price_paid',
            'currency', 'quantity', 'checkin_status', 'checked_in_at', 'qr_code',
            'qr_code_data', 'transfer_status', 'transferred_to', 'transferred_at',
            'notes', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'checked_in_at', 'qr_code', 'transferred_at',
            'created_at', 'updated_at', 'ticket_type_name', 'event_title',
            'order_number', 'attendee_name'
        ]
    
    def get_qr_code_data(self, obj):
        """Get QR code data URL"""
        if obj.qr_code:
            return obj.qr_code.url
        return None


class TicketListSerializer(serializers.ModelSerializer):
    """Ticket list serializer (minimal fields)"""
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    event_title = serializers.CharField(source='ticket_type.event.title', read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'ticket_type_name', 'event_title',
            'status', 'price_paid', 'quantity', 'checkin_status', 'created_at'
        ]


class TicketCheckInSerializer(serializers.Serializer):
    """Ticket check-in serializer"""
    ticket_id = serializers.UUIDField()
    checked_in_by_id = serializers.UUIDField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_ticket_id(self, value):
        """Validate ticket exists"""
        try:
            Ticket.objects.get(id=value)
        except Ticket.DoesNotExist:
            raise serializers.ValidationError("Ticket not found")
        return value


class TicketTransferSerializer(serializers.Serializer):
    """Ticket transfer serializer"""
    ticket_id = serializers.UUIDField()
    transferred_to = serializers.CharField(help_text="Email of new attendee")
    
    def validate_transferred_to(self, value):
        """Validate email format"""
        if '@' not in value:
            raise serializers.ValidationError("Invalid email format")
        return value


class TicketBulkCheckInSerializer(serializers.Serializer):
    """Bulk check-in serializer"""
    ticket_ids = serializers.ListField(child=serializers.UUIDField())
    checked_in_by_id = serializers.UUIDField(required=False)
    
    def validate_ticket_ids(self, value):
        """Validate at least one ticket"""
        if not value:
            raise serializers.ValidationError("At least one ticket ID is required")
        if len(value) > 1000:
            raise serializers.ValidationError("Maximum 1000 tickets per operation")
        return value

