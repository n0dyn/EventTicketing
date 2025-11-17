from django.contrib import admin
from django.utils.html import format_html
from .models import TicketType, Ticket, PromoCode, PriceTier


class PriceTierInline(admin.TabularInline):
    """Inline admin for price tiers within ticket type"""
    model = PriceTier
    extra = 1
    fields = ('name', 'price', 'quantity', 'start_date', 'end_date')


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    """
    Admin interface for Ticket Types
    """
    list_display = ('name', 'event', 'price', 'quantity', 'sold_count', 'available_quantity', 'is_active', 'is_on_sale')
    list_filter = ('is_active', 'event__organization', 'sale_start', 'sale_end')
    search_fields = ('name', 'description', 'event__title')
    readonly_fields = ('sold_count', 'available_quantity', 'is_sold_out', 'is_on_sale', 'created_at', 'updated_at')
    inlines = [PriceTierInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'name', 'description')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'quantity', 'sold_count', 'available_quantity', 'is_sold_out')
        }),
        ('Sale Period', {
            'fields': ('sale_start', 'sale_end', 'is_on_sale')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'event__organization')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Admin interface for Individual Tickets
    """
    list_display = ('ticket_code', 'ticket_type', 'order', 'attendee_name', 'attendee_email', 'is_checked_in', 'created_at')
    list_filter = ('is_checked_in', 'ticket_type', 'created_at')
    search_fields = ('ticket_code', 'attendee_name', 'attendee_email', 'order__id')
    readonly_fields = ('ticket_code', 'qr_code', 'is_checked_in', 'checked_in_at', 'checked_in_by', 'created_at')
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_code', 'ticket_type', 'order', 'qr_code')
        }),
        ('Attendee Information', {
            'fields': ('attendee_name', 'attendee_email')
        }),
        ('Check-in Status', {
            'fields': ('is_checked_in', 'checked_in_at', 'checked_in_by')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ticket_type', 'order', 'checked_in_by')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """
    Admin interface for Promo Codes
    """
    list_display = ('code', 'event', 'discount_type', 'discount_value', 'used_count', 'max_uses', 'is_valid', 'valid_from', 'valid_until')
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_until')
    search_fields = ('code', 'event__title')
    readonly_fields = ('used_count', 'is_valid', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'code')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount_value')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'used_count')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until', 'is_valid')
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event')


@admin.register(PriceTier)
class PriceTierAdmin(admin.ModelAdmin):
    """
    Admin interface for Price Tiers
    """
    list_display = ('name', 'ticket_type', 'price', 'start_date', 'end_date', 'is_active')
    list_filter = ('ticket_type__event', 'start_date', 'end_date')
    search_fields = ('name', 'ticket_type__name', 'ticket_type__event__title')
    readonly_fields = ('is_active', 'created_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ticket_type', 'ticket_type__event')
