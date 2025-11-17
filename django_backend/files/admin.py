from django.contrib import admin
from django.utils.html import format_html
from .models import File


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """
    Admin interface for Files
    """
    list_display = ('filename', 'category', 'file_type', 'size_display', 'uploaded_by', 'created_at')
    list_filter = ('category', 'file_type', 'created_at', 'uploaded_by')
    search_fields = ('filename', 'original_filename', 'uploaded_by__email')
    readonly_fields = ('file_extension', 'is_image', 'is_document', 'size_mb', 'size_kb', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('File Information', {
            'fields': ('filename', 'original_filename', 'file', 'path', 'url')
        }),
        ('Metadata', {
            'fields': ('content_type', 'size', 'size_mb', 'size_kb', 'file_extension')
        }),
        ('Categorization', {
            'fields': ('category', 'file_type', 'is_image', 'is_document')
        }),
        ('Variants', {
            'fields': ('variants',),
            'classes': ('collapse',)
        }),
        ('Upload Information', {
            'fields': ('uploaded_by', 'created_at', 'updated_at')
        }),
    )
    
    def size_display(self, obj):
        """Display file size in a readable format"""
        if obj.size_mb >= 1:
            return f"{obj.size_mb} MB"
        else:
            return f"{obj.size_kb} KB"
    size_display.short_description = 'Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uploaded_by')
    
    def has_add_permission(self, request):
        return False  # Files should be uploaded through the system, not manually created
