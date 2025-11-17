"""
ViewSets and API endpoints for ticketing system enhancements
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from .ticket_enhancements import (
    TicketDisablement, TicketBlacklist, UserBan,
    TicketTransfer, EventMetrics, LocationMetrics
)
from .ticket_enhancement_serializers import (
    TicketDisablementSerializer, TicketBlacklistSerializer,
    UserBanSerializer, UserBanCreateSerializer,
    TicketTransferSerializer, TicketTransferCreateSerializer,
    EventMetricsSerializer, LocationMetricsSerializer
)
from tickets.models import Ticket
from events.models import Event
from attendees.models import CheckInLocation
from core.permissions import IsAdminUser, IsOrganizerOrAdmin

User = get_user_model()


# ============================================================================
# TICKET DISABLEMENT VIEWSET
# ============================================================================

class TicketDisablementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ticket disablements
    
    endpoints:
        GET    /api/v1/tickets/{ticket_id}/disablements/ - List disablements
        POST   /api/v1/tickets/{ticket_id}/disablements/ - Disable ticket
        GET    /api/v1/tickets/{ticket_id}/disablements/{id}/ - Get detail
        PATCH  /api/v1/tickets/{ticket_id}/disablements/{id}/re-enable/ - Re-enable
    """
    serializer_class = TicketDisablementSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrAdmin]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Only show disablements for tickets in user's events"""
        if self.request.user.is_staff:
            return TicketDisablement.objects.all()
        
        # Organizers can only see disablements for their events
        return TicketDisablement.objects.filter(
            ticket__ticket_type__event__owner=self.request.user
        )
    
    def create(self, request, ticket_id=None):
        """Disable a ticket"""
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Check permission
        if not (request.user.is_staff or 
                ticket.ticket_type.event.owner == request.user):
            raise PermissionDenied("Cannot disable tickets for this event")
        
        # Check if already disabled
        if TicketDisablement.objects.filter(
            ticket=ticket,
            re_enabled_at__isnull=True
        ).exists():
            return Response(
                {'error': 'Ticket is already disabled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create disablement record
        disablement = TicketDisablement.objects.create(
            ticket=ticket,
            status='disabled',
            reason=request.data.get('reason', 'other'),
            detailed_reason=request.data.get('detailed_reason', ''),
            disabled_by=request.user,
            evidence_data=request.data.get('evidence_data', {})
        )
        
        # Update ticket status
        ticket.status = 'disabled'
        ticket.save()
        
        serializer = self.get_serializer(disablement)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def re_enable(self, request, ticket_id=None, pk=None):
        """Re-enable a disabled ticket"""
        disablement = self.get_object()
        
        # Check permission
        if not request.user.is_staff:
            raise PermissionDenied("Only admins can re-enable tickets")
        
        disablement.re_enable(user=request.user)
        serializer = self.get_serializer(disablement)
        return Response(serializer.data)


# ============================================================================
# TICKET BLACKLIST VIEWSET
# ============================================================================

class TicketBlacklistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ticket blacklist entries
    
    endpoints:
        GET    /api/v1/tickets/blacklist/ - List blacklist entries
        POST   /api/v1/tickets/blacklist/ - Add to blacklist
        GET    /api/v1/tickets/blacklist/{id}/ - Get entry
        DELETE /api/v1/tickets/blacklist/{id}/ - Remove from blacklist
    """
    serializer_class = TicketBlacklistSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """Show blacklist entries based on permissions"""
        if self.request.user.is_staff:
            return TicketBlacklist.objects.all()
        
        # Organizers see only their event blacklists
        return TicketBlacklist.objects.filter(
            Q(event__owner=self.request.user) | Q(event__isnull=True)
        )
    
    @action(detail=False, methods=['post'])
    def check_ticket(self, request):
        """Check if a ticket is blacklisted"""
        ticket_id = request.data.get('ticket_id')
        ticket_code = request.data.get('ticket_code')
        
        if not ticket_id and not ticket_code:
            return Response(
                {'error': 'Provide ticket_id or ticket_code'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check blacklist
        is_blacklisted = TicketBlacklist.is_ticket_blacklisted(
            Ticket.objects.get(id=ticket_id) if ticket_id else 
            Ticket.objects.get(ticket_code=ticket_code)
        )
        
        return Response({'is_blacklisted': is_blacklisted})


# ============================================================================
# USER BAN VIEWSET
# ============================================================================

class UserBanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user bans
    
    endpoints:
        GET    /api/v1/users/{user_id}/bans/ - List user bans
        POST   /api/v1/users/{user_id}/bans/ - Ban user
        GET    /api/v1/users/{user_id}/bans/{id}/ - Get ban
        PATCH  /api/v1/users/{user_id}/bans/{id}/ - Update ban
        DELETE /api/v1/users/{user_id}/bans/{id}/ - Lift ban
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return UserBan.objects.filter(user_id=user_id)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserBanCreateSerializer
        return UserBanSerializer
    
    def create(self, request, user_id=None):
        """Ban a user from an event or globally"""
        user = get_object_or_404(User, id=user_id)
        
        # Check if already banned
        event_id = request.data.get('event')
        if UserBan.objects.filter(
            user=user,
            event_id=event_id,
        ).filter(Q(lifted_at__isnull=True) & Q(appeal_approved__isnull=True)).exists():
            return Response(
                {'error': 'User is already banned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UserBanCreateSerializer(data=request.data, context={'request': request})
        serializer.initial_data['user'] = user_id
        
        if serializer.is_valid():
            ban = serializer.save(user=user, issued_by=request.user)
            return Response(
                UserBanSerializer(ban).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def request_appeal(self, request, user_id=None, pk=None):
        """User requests appeal of ban"""
        ban = self.get_object()
        
        # Only the banned user can request appeal
        if request.user.id != ban.user.id:
            raise PermissionDenied("Can only request appeal for your own ban")
        
        ban.request_appeal(notes=request.data.get('notes', ''))
        return Response(UserBanSerializer(ban).data)
    
    @action(detail=True, methods=['post'])
    def approve_appeal(self, request, user_id=None, pk=None):
        """Approve ban appeal"""
        if not request.user.is_staff:
            raise PermissionDenied("Only admins can approve appeals")
        
        ban = self.get_object()
        ban.approve_appeal(reviewer=request.user)
        return Response(UserBanSerializer(ban).data)
    
    @action(detail=True, methods=['post'])
    def reject_appeal(self, request, user_id=None, pk=None):
        """Reject ban appeal"""
        if not request.user.is_staff:
            raise PermissionDenied("Only admins can reject appeals")
        
        ban = self.get_object()
        ban.reject_appeal(reviewer=request.user)
        return Response(UserBanSerializer(ban).data)
    
    @action(detail=True, methods=['post'])
    def lift(self, request, user_id=None, pk=None):
        """Lift a ban"""
        if not request.user.is_staff:
            raise PermissionDenied("Only admins can lift bans")
        
        ban = self.get_object()
        reason = request.data.get('reason', 'Admin action')
        ban.lift(user=request.user, reason=reason)
        return Response(UserBanSerializer(ban).data)


# ============================================================================
# TICKET TRANSFER VIEWSET
# ============================================================================

class TicketTransferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ticket transfers
    
    endpoints:
        GET    /api/v1/tickets/{ticket_id}/transfers/ - List transfers
        POST   /api/v1/tickets/{ticket_id}/transfers/ - Create transfer
        GET    /api/v1/tickets/{ticket_id}/transfers/{id}/ - Get transfer
        PATCH  /api/v1/tickets/{ticket_id}/transfers/{id}/accept/ - Accept
        PATCH  /api/v1/tickets/{ticket_id}/transfers/{id}/decline/ - Decline
    """
    serializer_class = TicketTransferSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        # Users can see transfers for tickets they own or are offered to them
        return TicketTransfer.objects.filter(
            Q(ticket_id=ticket_id) &
            (Q(from_user=self.request.user) | Q(to_user=self.request.user))
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TicketTransferCreateSerializer
        return TicketTransferSerializer
    
    def create(self, request, ticket_id=None):
        """Create a ticket transfer offer"""
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        # Check ownership
        if ticket.order.user != request.user:
            raise PermissionDenied("Can only transfer tickets you own")
        
        # Check if ticket is transferable
        if ticket.status not in ['active', 'transferred']:
            return Response(
                {'error': 'This ticket cannot be transferred'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TicketTransferCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.initial_data['ticket'] = ticket_id
        
        if serializer.is_valid():
            transfer = serializer.save(from_user=request.user, ticket=ticket)
            return Response(
                TicketTransferSerializer(transfer).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, ticket_id=None, pk=None):
        """Accept a ticket transfer"""
        transfer = self.get_object()
        
        # Only recipient can accept
        if transfer.to_user != request.user:
            raise PermissionDenied("Only the recipient can accept this transfer")
        
        # Check if expired
        if transfer.is_expired:
            transfer.status = 'expired'
            transfer.save()
            return Response(
                {'error': 'Transfer offer has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if ban blocks recipient
        if UserBan.is_user_banned(request.user, transfer.ticket.event):
            return Response(
                {'error': 'You are banned from this event'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        transfer.accept()
        return Response(TicketTransferSerializer(transfer).data)
    
    @action(detail=True, methods=['post'])
    def decline(self, request, ticket_id=None, pk=None):
        """Decline a ticket transfer"""
        transfer = self.get_object()
        
        # Only recipient can decline
        if transfer.to_user != request.user:
            raise PermissionDenied("Only the recipient can decline this transfer")
        
        reason = request.data.get('reason', '')
        transfer.decline(reason=reason)
        return Response(TicketTransferSerializer(transfer).data)


# ============================================================================
# EVENT METRICS VIEWSET
# ============================================================================

class EventMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for event metrics
    
    endpoints:
        GET    /api/v1/events/{event_id}/metrics/ - Get event metrics
    """
    serializer_class = EventMetricsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrAdmin]
    
    def get_queryset(self):
        return EventMetrics.objects.all()
    
    def get_object(self):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        
        # Check permission
        if not (self.request.user.is_staff or event.owner == self.request.user):
            raise PermissionDenied("Cannot view metrics for this event")
        
        # Get or create metrics
        metrics, _ = EventMetrics.objects.get_or_create(event=event)
        return metrics
    
    def retrieve(self, request, *args, **kwargs):
        """Get event metrics"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ============================================================================
# LOCATION METRICS VIEWSET
# ============================================================================

class LocationMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for location metrics
    
    endpoints:
        GET    /api/v1/events/{event_id}/location-metrics/ - List location metrics
        GET    /api/v1/events/{event_id}/location-metrics/{id}/ - Get location metrics
    """
    serializer_class = LocationMetricsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrAdmin]
    
    def get_queryset(self):
        event_id = self.kwargs.get('event_id')
        event = get_object_or_404(Event, id=event_id)
        
        # Check permission
        if not (self.request.user.is_staff or event.owner == self.request.user):
            raise PermissionDenied("Cannot view metrics for this event")
        
        return LocationMetrics.objects.filter(event=event)
    
    @action(detail=False, methods=['get'])
    def today(self, request, event_id=None):
        """Get today's location metrics"""
        queryset = self.get_queryset().filter(date=timezone.now().date())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def hourly(self, request, event_id=None):
        """Get hourly metrics for today"""
        queryset = self.get_queryset().filter(
            date=timezone.now().date()
        ).order_by('hour')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ============================================================================
# ENFORCEMENT MIDDLEWARE
# ============================================================================

def check_user_banned(user, event):
    """Check if user is banned from event"""
    return UserBan.is_user_banned(user, event)


def check_ticket_blacklisted(ticket):
    """Check if ticket is blacklisted"""
    return TicketBlacklist.is_ticket_blacklisted(ticket)


def disable_ticket(ticket, reason, user, detailed_reason='', evidence=None):
    """Disable a ticket with audit trail"""
    TicketDisablement.objects.create(
        ticket=ticket,
        status='disabled',
        reason=reason,
        detailed_reason=detailed_reason,
        disabled_by=user,
        evidence_data=evidence or {}
    )
    ticket.status = 'disabled'
    ticket.save()


def ban_user(user, event, reason, description, issued_by, evidence=None):
    """Ban a user from event/globally with audit trail"""
    return UserBan.objects.create(
        user=user,
        event=event,
        reason=reason,
        description=description,
        issued_by=issued_by,
        evidence=evidence or {}
    )

