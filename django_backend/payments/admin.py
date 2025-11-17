from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin interface for Payments
    """
    list_display = ('id', 'order', 'amount', 'currency', 'status', 'provider', 'is_successful', 'created_at')
    list_filter = ('status', 'provider', 'currency', 'created_at')
    search_fields = ('id', 'order__id', 'provider_payment_id', 'provider_charge_id')
    readonly_fields = ('id', 'net_amount', 'is_successful', 'can_be_refunded', 'created_at', 'updated_at', 'processed_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('id', 'order', 'amount', 'currency', 'status')
        }),
        ('Provider Details', {
            'fields': ('provider', 'provider_payment_id', 'provider_payment_intent_id', 'provider_charge_id')
        }),
        ('Financial Details', {
            'fields': ('transaction_fee', 'net_amount')
        }),
        ('Metadata', {
            'fields': ('payment_method_details', 'provider_response', 'failure_reason'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_successful', 'can_be_refunded')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'order__user')
    
    def has_add_permission(self, request):
        return False  # Payments should be created through the system, not manually


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """
    Admin interface for Refunds
    """
    list_display = ('id', 'payment', 'amount', 'currency', 'status', 'reason', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('id', 'payment__id', 'provider_refund_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'processed_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('id', 'payment', 'amount', 'currency', 'reason')
        }),
        ('Provider Details', {
            'fields': ('provider_refund_id', 'provider_response')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('payment', 'payment__order')
    
    def has_add_permission(self, request):
        return False  # Refunds should be created through the system, not manually
