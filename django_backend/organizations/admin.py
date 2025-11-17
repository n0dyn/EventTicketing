from django.contrib import admin
from django.utils.html import format_html
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Admin interface for Organizations
    """
    list_display = ('name', 'email', 'website', 'city', 'country', 'is_active', 'is_verified', 'member_count', 'event_count', 'created_at')
    list_filter = ('is_active', 'is_verified', 'country', 'created_at')
    search_fields = ('name', 'email', 'website', 'city')
    readonly_fields = ('created_at', 'updated_at', 'member_count', 'event_count')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'logo')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Statistics', {
            'fields': ('member_count', 'event_count', 'created_at', 'updated_at')
        }),
    )
    
    def member_count(self, obj):
        """Display member count"""
        count = obj.get_member_count()
        return format_html('<strong>{}</strong>', count)
    member_count.short_description = 'Members'
    
    def event_count(self, obj):
        """Display event count"""
        count = obj.get_event_count()
        return format_html('<strong>{}</strong>', count)
    event_count.short_description = 'Events'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('members', 'events')
