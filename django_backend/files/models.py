from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import FileExtensionValidator
import uuid
import os


class FileCategory(models.TextChoices):
    """Choices for file categories"""
    EVENTS = 'events', 'Events'
    USERS = 'users', 'Users'
    DOCUMENTS = 'documents', 'Documents'
    ORGANIZATIONS = 'organizations', 'Organizations'
    TICKETS = 'tickets', 'Tickets'
    OTHER = 'other', 'Other'


class FileType(models.TextChoices):
    """Choices for file types"""
    IMAGE = 'image', 'Image'
    DOCUMENT = 'document', 'Document'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'
    ARCHIVE = 'archive', 'Archive'
    OTHER = 'other', 'Other'


def file_upload_path(instance, filename):
    """Generate upload path for files"""
    category = instance.category or 'other'
    file_type = instance.file_type or 'other'
    return f'files/{category}/{file_type}/{filename}'


class File(models.Model):
    """
    Model for storing file metadata and managing file uploads
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File identification
    filename = models.CharField(max_length=255, db_index=True)
    original_filename = models.CharField(max_length=255, blank=True)
    
    # File metadata
    content_type = models.CharField(max_length=100)
    size = models.BigIntegerField(help_text='File size in bytes')
    category = models.CharField(
        max_length=50,
        choices=FileCategory.choices,
        default=FileCategory.OTHER,
        db_index=True
    )
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.OTHER
    )
    
    # File storage
    file = models.FileField(
        upload_to=file_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip', 'mp4', 'mp3']
            )
        ]
    )
    path = models.CharField(max_length=500, unique=True, help_text='Relative path to file')
    url = models.URLField(max_length=500, blank=True, help_text='Public URL')
    
    # Image variants (for resized images, thumbnails, etc.)
    variants = models.JSONField(default=dict, blank=True, help_text='JSON of file variants')
    
    # Relationships
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='uploaded_files'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'File'
        verbose_name_plural = 'Files'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'file_type']),
            models.Index(fields=['uploaded_by', 'created_at']),
        ]

    def __str__(self):
        return f"{self.filename} ({self.category})"

    def save(self, *args, **kwargs):
        # Set path if not provided
        if not self.path and self.file:
            self.path = self.file.name
        
        # Set original filename if not provided
        if not self.original_filename:
            self.original_filename = self.filename
        
        # Generate URL if not provided
        if not self.url and self.file:
            self.url = self.file.url
        
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.filename)[1].lower()

    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_type == FileType.IMAGE

    @property
    def is_document(self):
        """Check if file is a document"""
        return self.file_type == FileType.DOCUMENT

    @property
    def size_mb(self):
        """Get file size in MB"""
        return round(self.size / (1024 * 1024), 2)

    @property
    def size_kb(self):
        """Get file size in KB"""
        return round(self.size / 1024, 2)

    def get_variant(self, variant_name):
        """Get a specific file variant"""
        return self.variants.get(variant_name)

    def add_variant(self, variant_name, variant_data):
        """Add a file variant"""
        if not self.variants:
            self.variants = {}
        self.variants[variant_name] = variant_data
        self.save(update_fields=['variants'])

    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        if self.file:
            try:
                self.file.delete(save=False)
            except Exception:
                pass  # File might already be deleted
        super().delete(*args, **kwargs)
