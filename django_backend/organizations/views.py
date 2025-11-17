"""
Organization views for Django REST Framework
"""
from rest_framework import generics, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Organization
from .serializers import (
    OrganizationSerializer, OrganizationCreateSerializer,
    OrganizationUpdateSerializer, OrganizationListSerializer
)


class OrganizationListCreateView(generics.ListCreateAPIView):
    """List and create organizations"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'country', 'state']
    search_fields = ['name', 'description', 'city']
    ordering_fields = ['name', 'created_at', 'member_count', 'event_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrganizationCreateSerializer
        return OrganizationListSerializer
    
    def get_queryset(self):
        # Users can see organizations they're members of or public organizations
        if self.request.user.is_staff:
            return Organization.objects.all()
        return Organization.objects.filter(
            userorganizations__user=self.request.user
        ).distinct()


class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an organization"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return OrganizationUpdateSerializer
        return OrganizationSerializer
    
    def get_queryset(self):
        # Users can access organizations they're members of
        if self.request.user.is_staff:
            return Organization.objects.all()
        return Organization.objects.filter(
            userorganizations__user=self.request.user
        ).distinct()
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_organizations(request):
    """Get organizations for current user"""
    organizations = Organization.objects.filter(
        userorganizations__user=request.user
    ).distinct()
    serializer = OrganizationListSerializer(organizations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def organization_stats(request, pk):
    """Get organization statistics"""
    try:
        organization = Organization.objects.get(pk=pk)
        
        # Check if user has access to this organization
        if not request.user.is_staff:
            if not organization.userorganizations.filter(user=request.user).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=403
                )
        
        stats = {
            'id': organization.id,
            'name': organization.name,
            'member_count': organization.get_member_count(),
            'event_count': organization.get_event_count(),
            'created_at': organization.created_at,
            'is_active': organization.is_active
        }
        
        return Response(stats)
    except Organization.DoesNotExist:
        return Response(
            {'error': 'Organization not found'},
            status=404
        )