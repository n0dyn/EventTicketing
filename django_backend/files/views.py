"""
File views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import File
from .serializers import (
    FileSerializer, FileListSerializer, FileCreateSerializer,
    FileUpdateSerializer, FileUploadSerializer, BulkFileUploadSerializer,
    FileBatchOperationSerializer
)


class FileViewSet(viewsets.ModelViewSet):
    """File viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['organization', 'file_type', 'is_public', 'uploaded_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'downloads']
    ordering = ['-created_at']
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FileCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FileUpdateSerializer
        elif self.action == 'list':
            return FileListSerializer
        elif self.action == 'bulk_upload':
            return BulkFileUploadSerializer
        return FileSerializer
    
    def get_queryset(self):
        queryset = File.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(organization__userorganizations__user=self.request.user) |
                Q(is_public=True)
            ).distinct()
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Download file and increment counter"""
        file_obj = self.get_object()
        file_obj.downloads = (file_obj.downloads or 0) + 1
        file_obj.save()
        
        return Response({
            'status': 'success',
            'file_url': file_obj.file.url,
            'downloads': file_obj.downloads
        })
    
    @action(detail=True, methods=['post'])
    def make_public(self, request, pk=None):
        """Make file public"""
        file_obj = self.get_object()
        file_obj.is_public = True
        file_obj.save()
        
        return Response({
            'status': 'success',
            'file': FileSerializer(file_obj, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def make_private(self, request, pk=None):
        """Make file private"""
        file_obj = self.get_object()
        file_obj.is_public = False
        file_obj.save()
        
        return Response({
            'status': 'success',
            'file': FileSerializer(file_obj, context={'request': request}).data
        })
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload single file"""
        serializer = FileUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                file_obj = File.objects.create(
                    organization_id=serializer.validated_data['organization_id'],
                    file=serializer.validated_data['file'],
                    name=serializer.validated_data.get('name', serializer.validated_data['file'].name),
                    description=serializer.validated_data.get('description', ''),
                    is_public=serializer.validated_data['is_public'],
                    uploaded_by=request.user
                )
                
                return Response({
                    'status': 'success',
                    'file': FileSerializer(file_obj, context={'request': request}).data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        """Upload multiple files"""
        serializer = BulkFileUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            files = serializer.validated_data['files']
            organization_id = serializer.validated_data['organization_id']
            is_public = serializer.validated_data['is_public']
            
            created_files = []
            failed_count = 0
            
            for file_obj in files:
                try:
                    file = File.objects.create(
                        organization_id=organization_id,
                        file=file_obj,
                        name=file_obj.name,
                        is_public=is_public,
                        uploaded_by=request.user
                    )
                    created_files.append(file)
                except Exception:
                    failed_count += 1
            
            return Response({
                'status': 'success',
                'created': len(created_files),
                'failed': failed_count,
                'files': FileSerializer(created_files, many=True, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def batch_operation(self, request):
        """Perform batch operation on files"""
        serializer = FileBatchOperationSerializer(data=request.data)
        
        if serializer.is_valid():
            file_ids = serializer.validated_data['file_ids']
            operation = serializer.validated_data['operation']
            
            files = File.objects.filter(id__in=file_ids)
            
            if operation == 'delete':
                count = files.count()
                files.delete()
                return Response({
                    'status': 'success',
                    'deleted': count
                })
            
            elif operation == 'make_public':
                count = files.update(is_public=True)
                return Response({
                    'status': 'success',
                    'updated': count
                })
            
            elif operation == 'make_private':
                count = files.update(is_public=False)
                return Response({
                    'status': 'success',
                    'updated': count
                })
            
            elif operation == 'download':
                return Response({
                    'status': 'success',
                    'files': [
                        {
                            'name': f.name,
                            'url': f.file.url
                        } for f in files
                    ]
                })
            
            else:
                return Response(
                    {'error': f'Unknown operation: {operation}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get file statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_files': queryset.count(),
            'total_downloads': sum(f.downloads or 0 for f in queryset),
            'by_type': {},
            'public': queryset.filter(is_public=True).count(),
            'private': queryset.filter(is_public=False).count()
        }
        
        # Group by type
        for file_type in queryset.values('file_type').distinct():
            count = queryset.filter(file_type=file_type['file_type']).count()
            stats['by_type'][file_type['file_type']] = count
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get file details with full metadata"""
        file_obj = self.get_object()
        
        details = {
            'file': FileSerializer(file_obj, context={'request': request}).data,
            'metadata': file_obj.metadata or {},
            'downloads': file_obj.downloads,
            'created_at': file_obj.created_at,
            'uploaded_by': file_obj.uploaded_by.full_name
        }
        
        return Response(details)
    
    @action(detail=False, methods=['get'])
    def my_uploads(self, request):
        """Get current user's file uploads"""
        queryset = self.get_queryset().filter(uploaded_by=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
