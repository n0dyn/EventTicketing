from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, Cart, CartItem


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items within order"""
    model = OrderItem
    extra = 0
    fields = ('ticket_type', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin interface for Orders
    """
    list_display = ('order_number', 'user', 'event', 'status', 'total_amount', 'currency', 'payment_method', 'get_ticket_count', 'created_at')
    list_filter = ('status', 'payment_method', 'currency', 'created_at', 'completed_at')
    search_fields = ('id', 'user__email', 'billing_email', 'transaction_id')
    readonly_fields = ('order_number', 'subtotal', 'discount_amount', 'total_amount', 'get_ticket_count', 'created_at', 'updated_at', 'completed_at')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'event', 'status')
        }),
        ('Totals', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'currency')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_intent_id', 'transaction_id')
        }),
        ('Promo Code', {
            'fields': ('promo_code',)
        }),
        ('Billing Information', {
            'fields': ('billing_email', 'billing_first_name', 'billing_last_name', 
                      'billing_address_line_1', 'billing_address_line_2', 
                      'billing_city', 'billing_state', 'billing_postal_code', 'billing_country'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('get_ticket_count', 'created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'event', 'promo_code').prefetch_related('order_items')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Admin interface for Order Items
    """
    list_display = ('order', 'ticket_type', 'quantity', 'unit_price', 'total_price')
    list_filter = ('ticket_type__event', 'created_at')
    search_fields = ('order__id', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('total_price', 'created_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'ticket_type', 'ticket_type__event')


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items within cart"""
    model = CartItem
    extra = 0
    fields = ('ticket_type', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('unit_price', 'total_price')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin interface for Shopping Carts
    """
    list_display = ('user', 'total_items', 'total_amount', 'created_at', 'updated_at', 'expires_at', 'is_expired')
    list_filter = ('created_at', 'updated_at', 'expires_at')
    search_fields = ('user__email',)
    readonly_fields = ('total_items', 'total_amount', 'is_expired', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'expires_at')
        }),
        ('Statistics', {
            'fields': ('total_items', 'total_amount', 'is_expired')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('cart_items')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin interface for Cart Items
    """
    list_display = ('cart', 'ticket_type', 'quantity', 'unit_price', 'total_price', 'created_at')
    list_filter = ('ticket_type__event', 'created_at')
    search_fields = ('cart__user__email', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('unit_price', 'total_price', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cart', 'cart__user', 'ticket_type', 'ticket_type__event')
