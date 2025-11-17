"""
File serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import File


class FileSerializer(serializers.ModelSerializer):
    """File serializer"""
    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, allow_null=True)
    file_size_mb = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = File
        fields = [
            'id', 'organization', 'organization_name', 'uploaded_by', 'uploaded_by_name',
            'name', 'slug', 'file', 'file_url', 'file_type', 'file_size_mb', 'mime_type',
            'description', 'tags', 'is_public', 'downloads', 'variants', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'file_size_mb', 'file_url', 'mime_type', 'downloads',
            'created_at', 'updated_at', 'organization_name', 'uploaded_by_name'
        ]
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file:
            size_mb = obj.file.size / (1024 * 1024)
            return round(size_mb, 2)
        return None
    
    def get_file_url(self, obj):
        """Get full file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class FileListSerializer(serializers.ModelSerializer):
    """File list serializer (minimal fields)"""
    file_size_mb = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = File
        fields = [
            'id', 'name', 'file_type', 'file_size_mb', 'uploaded_by_name',
            'downloads', 'is_public', 'created_at'
        ]
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file:
            size_mb = obj.file.size / (1024 * 1024)
            return round(size_mb, 2)
        return None


class FileCreateSerializer(serializers.ModelSerializer):
    """File creation serializer"""
    
    class Meta:
        model = File
        fields = [
            'organization', 'file', 'name', 'description', 'tags', 'is_public'
        ]
    
    def validate_file(self, value):
        """Validate file"""
        # Check file size (max 100MB)
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 100MB")
        
        # Check file type if needed
        allowed_types = ['image', 'pdf', 'document', 'video', 'audio']
        file_type = value.content_type.split('/')[0]
        
        return value


class FileUpdateSerializer(serializers.ModelSerializer):
    """File update serializer"""
    
    class Meta:
        model = File
        fields = [
            'name', 'description', 'tags', 'is_public'
        ]


class FileUploadSerializer(serializers.Serializer):
    """File upload serializer"""
    file = serializers.FileField()
    organization_id = serializers.UUIDField()
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    is_public = serializers.BooleanField(default=False)


class BulkFileUploadSerializer(serializers.Serializer):
    """Bulk file upload serializer"""
    files = serializers.ListField(child=serializers.FileField())
    organization_id = serializers.UUIDField()
    is_public = serializers.BooleanField(default=False)
    
    def validate_files(self, value):
        """Validate file list"""
        if not value:
            raise serializers.ValidationError("At least one file is required")
        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 files per upload")
        return value


class FileVariantSerializer(serializers.Serializer):
    """File variant serializer"""
    type = serializers.CharField()
    size = serializers.CharField(required=False)
    url = serializers.URLField()
    created_at = serializers.DateTimeField()


class FileMetadataSerializer(serializers.Serializer):
    """File metadata serializer"""
    original_filename = serializers.CharField()
    file_format = serializers.CharField()
    dimensions = serializers.DictField(required=False)
    duration = serializers.FloatField(required=False)
    codec = serializers.CharField(required=False)


class FileBatchOperationSerializer(serializers.Serializer):
    """Batch file operation serializer"""
    file_ids = serializers.ListField(child=serializers.UUIDField())
    operation = serializers.CharField()  # delete, make_public, make_private, download
    
    def validate_operation(self, value):
        """Validate operation"""
        valid_operations = ['delete', 'make_public', 'make_private', 'download']
        if value not in valid_operations:
            raise serializers.ValidationError(f"Operation must be one of: {', '.join(valid_operations)}")
        return value
    
    def validate_file_ids(self, value):
        """Validate file list"""
        if not value:
            raise serializers.ValidationError("At least one file ID is required")
        if len(value) > 1000:
            raise serializers.ValidationError("Maximum 1000 files per operation")
        return value


class FileShareSerializer(serializers.Serializer):
    """File share serializer"""
    file_id = serializers.UUIDField()
    email = serializers.EmailField()
    permission = serializers.CharField(default='view')  # view, download
    expiry_days = serializers.IntegerField(required=False, default=7)


class ImageProcessingSerializer(serializers.Serializer):
    """Image processing serializer"""
    file_id = serializers.UUIDField()
    operation = serializers.CharField()  # resize, crop, rotate, compress
    parameters = serializers.JSONField()

