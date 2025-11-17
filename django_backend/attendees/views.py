"""
Attendee views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    Attendee, EventWaitlist, WaitlistEntry, WaitlistNotification,
    CheckIn, TicketQRCode
)
from .serializers import (
    AttendeeSerializer, AttendeeListSerializer, AttendeeCreateSerializer,
    AttendeeUpdateSerializer, EventWaitlistSerializer, EventWaitlistDetailSerializer,
    WaitlistEntrySerializer, WaitlistJoinSerializer, CheckInSerializer,
    CheckInListSerializer, BulkCheckInSerializer, TicketQRCodeSerializer
)


class TicketQRCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """Ticket QR code read-only viewset"""
    serializer_class = TicketQRCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ticket', 'is_used']
    
    def get_queryset(self):
        queryset = TicketQRCode.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(ticket__ticket_type__event__owner=self.request.user) |
                Q(ticket__ticket_type__event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset


class CheckInViewSet(viewsets.ModelViewSet):
    """Check-in viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ticket', 'attendee', 'check_in_method']
    search_fields = ['attendee__name', 'ticket__ticket_number']
    ordering_fields = ['checked_in_at', 'created_at']
    ordering = ['-checked_in_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CheckInListSerializer
        return CheckInSerializer
    
    def get_queryset(self):
        queryset = CheckIn.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(ticket__ticket_type__event__owner=self.request.user) |
                Q(ticket__ticket_type__event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_check_in(self, request):
        """Bulk check in attendees"""
        serializer = BulkCheckInSerializer(data=request.data)
        
        if serializer.is_valid():
            ticket_ids = serializer.validated_data['ticket_ids']
            checked_in_count = 0
            failed_count = 0
            
            for ticket_id in ticket_ids:
                try:
                    from tickets.models import Ticket
                    ticket = Ticket.objects.get(id=ticket_id)
                    
                    CheckIn.objects.create(
                        ticket=ticket,
                        checked_in_by=request.user,
                        check_in_method=serializer.validated_data.get('check_in_method', 'manual'),
                        check_in_location=serializer.validated_data.get('check_in_location', '')
                    )
                    
                    ticket.checkin_status = 'checked_in'
                    ticket.checked_in_at = timezone.now()
                    ticket.save()
                    checked_in_count += 1
                except:
                    failed_count += 1
            
            return Response({
                'checked_in': checked_in_count,
                'failed': failed_count,
                'total': len(ticket_ids)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get check-in statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_check_ins': queryset.count(),
            'today': queryset.filter(checked_in_at__date=timezone.now().date()).count(),
            'by_method': {}
        }
        return Response(stats)


class AttendeeViewSet(viewsets.ModelViewSet):
    """Attendee viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event', 'attended', 'user']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AttendeeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttendeeUpdateSerializer
        elif self.action == 'list':
            return AttendeeListSerializer
        return AttendeeSerializer
    
    def get_queryset(self):
        queryset = Attendee.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(event__owner=self.request.user) |
                Q(event__organization__userorganizations__user=self.request.user) |
                Q(user=self.request.user)
            ).distinct()
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_attendances(self, request):
        """Get current user's attendances"""
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get attendee statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_attendees': queryset.count(),
            'attended': queryset.filter(attended=True).count(),
            'not_attended': queryset.filter(attended=False).count()
        }
        return Response(stats)


class WaitlistEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Waitlist entry read-only viewset"""
    serializer_class = WaitlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['waitlist', 'notified']
    ordering_fields = ['position', 'created_at']
    ordering = ['position']
    
    def get_queryset(self):
        queryset = WaitlistEntry.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(waitlist__event__owner=self.request.user) |
                Q(waitlist__event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset


class EventWaitlistViewSet(viewsets.ModelViewSet):
    """Event waitlist viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['event', 'is_active']
    ordering_fields = ['created_at']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventWaitlistDetailSerializer
        return EventWaitlistSerializer
    
    def get_queryset(self):
        queryset = EventWaitlist.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(event__owner=self.request.user) |
                Q(event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join waitlist for an event"""
        waitlist = self.get_object()
        serializer = WaitlistJoinSerializer(data=request.data)
        
        if serializer.is_valid():
            if not waitlist.is_active:
                return Response(
                    {'error': 'Waitlist is not active'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if already in waitlist
            if WaitlistEntry.objects.filter(
                waitlist=waitlist,
                attendee__email=serializer.validated_data['email']
            ).exists():
                return Response(
                    {'error': 'Already on waitlist'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create attendee if needed
            attendee, _ = Attendee.objects.get_or_create(
                event=waitlist.event,
                email=serializer.validated_data['email'],
                defaults={
                    'name': serializer.validated_data['name'],
                    'phone': serializer.validated_data.get('phone', '')
                }
            )
            
            # Add to waitlist
            position = waitlist.entries.count() + 1
            entry = WaitlistEntry.objects.create(
                waitlist=waitlist,
                attendee=attendee,
                position=position
            )
            
            return Response({
                'status': 'success',
                'message': f'Added to waitlist at position {position}',
                'entry': WaitlistEntrySerializer(entry).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def notify_entries(self, request, pk=None):
        """Notify waitlist entries that tickets are available"""
        waitlist = self.get_object()
        available_count = request.data.get('available_count', 1)
        
        entries = waitlist.entries.filter(notified=False)[:available_count]
        notified_count = 0
        
        for entry in entries:
            # Send notification
            WaitlistNotification.objects.create(
                entry=entry,
                notification_type='available',
                status='sent',
                message=f'A ticket is now available for {waitlist.event.title}'
            )
            
            entry.notified = True
            entry.notified_at = timezone.now()
            entry.save()
            notified_count += 1
        
        return Response({
            'status': 'success',
            'notified': notified_count
        })
    
    @action(detail=True, methods=['post'])
    def remove_entry(self, request, pk=None):
        """Remove entry from waitlist"""
        waitlist = self.get_object()
        entry_id = request.data.get('entry_id')
        
        try:
            entry = WaitlistEntry.objects.get(id=entry_id, waitlist=waitlist)
            entry.delete()
            
            # Reorder remaining entries
            remaining = waitlist.entries.all().order_by('created_at')
            for idx, e in enumerate(remaining, 1):
                e.position = idx
                e.save()
            
            return Response({
                'status': 'success',
                'message': 'Entry removed from waitlist'
            })
        except WaitlistEntry.DoesNotExist:
            return Response(
                {'error': 'Entry not found'},
                status=status.HTTP_404_NOT_FOUND
            )
