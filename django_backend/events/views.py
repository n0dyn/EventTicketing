"""
Event views for Django REST Framework
"""
from rest_framework import generics, permissions, filters, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Event, EventCategory, EventSeries, RecurrencePattern, EventInstance
from .serializers import (
    EventSerializer, EventCreateSerializer, EventUpdateSerializer,
    EventListSerializer, EventCategorySerializer, EventSeriesSerializer,
    RecurrencePatternSerializer, EventInstanceSerializer, EventPublishSerializer
)


class EventCategoryListCreateView(generics.ListCreateAPIView):
    """List and create event categories"""
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'event_count']
    ordering = ['name']


class EventCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an event category"""
    queryset = EventCategory.objects.all()
    serializer_class = EventCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class EventViewSet(ModelViewSet):
    """Event viewset with full CRUD operations"""
    queryset = Event.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_published', 'category', 'organization', 'city', 'state', 'country']
    search_fields = ['title', 'description', 'location', 'city', 'state', 'tags']
    ordering_fields = ['start_datetime', 'created_at', 'title', 'capacity']
    ordering = ['-start_datetime']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        elif self.action == 'list':
            return EventListSerializer
        return EventSerializer
    
    def get_queryset(self):
        queryset = Event.objects.all()
        
        # Filter by user's organizations if not admin
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(organization__userorganizations__user=self.request.user) |
                Q(owner=self.request.user)
            ).distinct()
        
        # Additional filters
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        is_published = self.request.query_params.get('is_published')
        if is_published is not None:
            queryset = queryset.filter(is_published=is_published.lower() == 'true')
        
        # Date filters
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(start_datetime__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(start_datetime__date__lte=end_date)
        
        # Past/upcoming filters
        show_past = self.request.query_params.get('show_past', 'false').lower() == 'true'
        if not show_past:
            queryset = queryset.filter(start_datetime__gte=timezone.now())
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish or unpublish an event"""
        event = self.get_object()
        serializer = EventPublishSerializer(data=request.data)
        
        if serializer.is_valid():
            publish = serializer.validated_data['publish']
            message = serializer.validated_data.get('message', '')
            
            if publish:
                event.is_published = True
                event.status = 'published'
            else:
                event.is_published = False
                event.status = 'draft'
            
            event.save()
            
            return Response({
                'message': f'Event {"published" if publish else "unpublished"} successfully',
                'event': EventSerializer(event).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an event"""
        event = self.get_object()
        reason = request.data.get('reason', '')
        
        event.status = 'cancelled'
        event.save()
        
        return Response({
            'message': 'Event cancelled successfully',
            'event': EventSerializer(event).data
        })
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events"""
        queryset = self.get_queryset().filter(
            start_datetime__gte=timezone.now(),
            is_published=True
        ).order_by('start_datetime')[:10]
        
        serializer = EventListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured events"""
        queryset = self.get_queryset().filter(
            featured_image__isnull=False,
            is_published=True,
            start_datetime__gte=timezone.now()
        ).order_by('?')[:6]  # Random 6 featured events
        
        serializer = EventListSerializer(queryset, many=True)
        return Response(serializer.data)


class EventSeriesViewSet(ModelViewSet):
    """Event series viewset for recurring events"""
    queryset = EventSeries.objects.all()
    serializer_class = EventSeriesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'organization']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'series_start_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = EventSeries.objects.select_related('organization', 'owner', 'recurrence_pattern')
        
        # Filter by user's organizations if not admin
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(organization__userorganizations__user=self.request.user) |
                Q(owner=self.request.user)
            ).distinct()
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def generate_events(self, request, pk=None):
        """Generate events for the series"""
        series = self.get_object()
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            events = series.generate_events(
                start_date=datetime.fromisoformat(start_date),
                end_date=datetime.fromisoformat(end_date)
            )
            
            return Response({
                'message': f'Generated {len(events)} events',
                'events': EventListSerializer(events, many=True).data
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RecurrencePatternViewSet(ModelViewSet):
    """Recurrence pattern viewset"""
    queryset = RecurrencePattern.objects.all()
    serializer_class = RecurrencePatternSerializer
    permission_classes = [permissions.IsAuthenticated]


class EventInstanceViewSet(ModelViewSet):
    """Event instance viewset for recurring event modifications"""
    queryset = EventInstance.objects.all()
    serializer_class = EventInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event_series', 'is_cancelled']


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_events(request):
    """Public events endpoint (no authentication required)"""
    queryset = Event.objects.filter(
        is_public=True,
        status='published'
    )
    
    # Apply filters
    category_id = request.query_params.get('category_id')
    if category_id:
        queryset = queryset.filter(categories__id=category_id)
    
    location = request.query_params.get('location')
    if location:
        queryset = queryset.filter(location__icontains=location)
    
    start_date = request.query_params.get('start_date')
    if start_date:
        queryset = queryset.filter(start_datetime__date__gte=start_date)
    
    end_date = request.query_params.get('end_date')
    if end_date:
        queryset = queryset.filter(start_datetime__date__lte=end_date)
    
    is_free = request.query_params.get('is_free')
    if is_free is not None:
        # This would need to be implemented based on ticket pricing
        pass
    
    # Order by start date
    queryset = queryset.order_by('start_datetime')
    
    # Pagination
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    queryset = queryset[offset:offset + limit]
    
    serializer = EventListSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def event_stats(request, pk):
    """Get event statistics"""
    try:
        event = Event.objects.get(pk=pk)
        
        # Check if user has access to this event
        if not request.user.is_staff:
            if not (event.organization.userorganizations.filter(user=request.user).exists() or
                    event.owner == request.user):
                return Response(
                    {'error': 'Access denied'},
                    status=403
                )
        
        stats = {
            'id': event.id,
            'title': event.title,
            'capacity': event.capacity,
            'capacity_remaining': event.capacity_remaining,
            'ticket_sales_total': event.ticket_sales_total,
            'ticket_sales_count': event.ticket_sales_count,
            'is_sold_out': event.is_sold_out,
            'status': event.status,
            'is_published': event.is_published,
            'start_datetime': event.start_datetime,
            'end_datetime': event.end_datetime
        }
        
        return Response(stats)
    except Event.DoesNotExist:
        return Response(
            {'error': 'Event not found'},
            status=404
        )