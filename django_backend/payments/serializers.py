"""
Payment serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    """Payment serializer"""
    order_number = serializers.CharField(source='order.order_number', read_only=True, allow_null=True)
    buyer_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'user', 'buyer_name', 'amount',
            'currency', 'payment_method', 'payment_method_display', 'status',
            'status_display', 'transaction_id', 'stripe_payment_intent_id',
            'stripe_customer_id', 'description', 'receipt_url', 'paid_at',
            'notes', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'stripe_payment_intent_id', 'stripe_customer_id',
            'receipt_url', 'paid_at', 'created_at', 'updated_at', 'order_number',
            'buyer_name', 'status_display', 'payment_method_display'
        ]


class PaymentListSerializer(serializers.ModelSerializer):
    """Payment list serializer (minimal fields)"""
    order_number = serializers.CharField(source='order.order_number', read_only=True, allow_null=True)
    buyer_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order_number', 'buyer_name', 'amount', 'currency',
            'payment_method', 'status', 'status_display', 'paid_at', 'created_at'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Payment creation serializer"""
    
    class Meta:
        model = Payment
        fields = [
            'order', 'amount', 'currency', 'payment_method', 'description'
        ]


class StripePaymentSerializer(serializers.Serializer):
    """Stripe payment serializer"""
    order_id = serializers.UUIDField()
    payment_method_id = serializers.CharField()
    save_card = serializers.BooleanField(default=False)


class StripeWebhookSerializer(serializers.Serializer):
    """Stripe webhook serializer"""
    type = serializers.CharField()
    data = serializers.JSONField()


class RefundSerializer(serializers.ModelSerializer):
    """Refund serializer"""
    payment_id = serializers.UUIDField(source='payment.id', read_only=True)
    order_number = serializers.CharField(source='payment.order.order_number', read_only=True)
    buyer_name = serializers.CharField(source='payment.user.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_id', 'order_number', 'buyer_name',
            'amount', 'reason', 'reason_display', 'status', 'status_display',
            'stripe_refund_id', 'refunded_at', 'notes', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'payment_id', 'stripe_refund_id', 'refunded_at',
            'created_at', 'updated_at', 'order_number', 'buyer_name',
            'status_display', 'reason_display'
        ]


class RefundListSerializer(serializers.ModelSerializer):
    """Refund list serializer (minimal fields)"""
    order_number = serializers.CharField(source='payment.order.order_number', read_only=True)
    buyer_name = serializers.CharField(source='payment.user.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'order_number', 'buyer_name', 'amount', 'reason',
            'status', 'status_display', 'refunded_at', 'created_at'
        ]


class RefundCreateSerializer(serializers.ModelSerializer):
    """Refund creation serializer"""
    
    class Meta:
        model = Refund
        fields = [
            'payment', 'amount', 'reason', 'notes'
        ]
    
    def validate_amount(self, value):
        """Validate refund amount"""
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be positive")
        return value


class RefundApproveSerializer(serializers.Serializer):
    """Refund approval serializer"""
    approval_notes = serializers.CharField(required=False, allow_blank=True)


class BulkRefundSerializer(serializers.Serializer):
    """Bulk refund creation serializer"""
    payment_ids = serializers.ListField(child=serializers.UUIDField())
    reason = serializers.CharField()
    amount_override = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_payment_ids(self, value):
        """Validate at least one payment"""
        if not value:
            raise serializers.ValidationError("At least one payment ID is required")
        if len(value) > 500:
            raise serializers.ValidationError("Maximum 500 payments per operation")
        return value


class PaymentMethodSerializer(serializers.Serializer):
    """Payment method serializer"""
    type = serializers.CharField()
    last_four = serializers.CharField(required=False)
    expiry_month = serializers.IntegerField(required=False)
    expiry_year = serializers.IntegerField(required=False)


class PaymentHistorySerializer(serializers.Serializer):
    """Payment history serializer"""
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    total_received = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()
    refund_count = serializers.IntegerField()

