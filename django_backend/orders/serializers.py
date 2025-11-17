"""
Order serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import Order, OrderItem, Cart, CartItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Order item serializer"""
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    event_title = serializers.CharField(source='ticket_type.event.title', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'ticket_type', 'ticket_type_name', 'event_title',
            'quantity', 'unit_price', 'discount_amount', 'promo_code',
            'subtotal', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'subtotal', 'created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    """Order serializer"""
    order_items = OrderItemSerializer(many=True, read_only=True)
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'buyer', 'buyer_name', 'event', 'event_title',
            'status', 'status_display', 'total_amount', 'currency', 'subtotal',
            'discount_total', 'tax_amount', 'service_charge', 'payment_method',
            'payment_status', 'notes', 'order_items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'discount_total', 'tax_amount',
            'service_charge', 'created_at', 'updated_at', 'buyer_name', 'event_title',
            'status_display'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Order list serializer (minimal fields)"""
    buyer_name = serializers.CharField(source='buyer.full_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'buyer_name', 'event_title', 'status',
            'status_display', 'total_amount', 'currency', 'created_at'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """Order creation serializer"""
    
    class Meta:
        model = Order
        fields = [
            'event', 'total_amount', 'currency', 'payment_method',
            'notes'
        ]


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Order update serializer"""
    
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'notes'
        ]


class CartItemSerializer(serializers.ModelSerializer):
    """Cart item serializer"""
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    event_title = serializers.CharField(source='ticket_type.event.title', read_only=True)
    unit_price = serializers.DecimalField(
        source='ticket_type.base_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'cart', 'ticket_type', 'ticket_type_name', 'event_title',
            'quantity', 'unit_price', 'subtotal', 'promo_code', 'added_at'
        ]
        read_only_fields = ['id', 'unit_price', 'subtotal', 'added_at']
    
    def get_subtotal(self, obj):
        """Calculate subtotal"""
        return str(obj.ticket_type.base_price * obj.quantity)
    
    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        if value > 1000:
            raise serializers.ValidationError("Maximum 1000 tickets per item")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Cart serializer"""
    items = CartItemSerializer(many=True, read_only=True)
    cart_total = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'item_count', 'cart_total', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'items', 'created_at', 'updated_at']
    
    def get_cart_total(self, obj):
        """Calculate total cart value"""
        total = sum(
            float(item.ticket_type.base_price) * item.quantity
            for item in obj.items.all()
        )
        return total
    
    def get_item_count(self, obj):
        """Count total items in cart"""
        return obj.items.aggregate(
            total=serializers.F('quantity')
        )['total'] or 0


class CartAddItemSerializer(serializers.Serializer):
    """Add item to cart serializer"""
    ticket_type_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1000)
    promo_code = serializers.CharField(required=False, allow_blank=True)


class CartUpdateItemSerializer(serializers.Serializer):
    """Update cart item quantity serializer"""
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class CartCheckoutSerializer(serializers.Serializer):
    """Cart checkout serializer"""
    payment_method = serializers.CharField()
    billing_name = serializers.CharField()
    billing_email = serializers.EmailField()
    billing_address = serializers.CharField()
    billing_city = serializers.CharField()
    billing_state = serializers.CharField()
    billing_postal_code = serializers.CharField()
    billing_country = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_payment_method(self, value):
        """Validate payment method"""
        valid_methods = ['stripe', 'paypal', 'manual']
        if value.lower() not in valid_methods:
            raise serializers.ValidationError(f"Payment method must be one of: {', '.join(valid_methods)}")
        return value.lower()


class BulkOrderSerializer(serializers.Serializer):
    """Bulk order creation serializer"""
    orders = OrderCreateSerializer(many=True)
    send_confirmation_email = serializers.BooleanField(default=True)

