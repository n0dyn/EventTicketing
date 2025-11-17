"""
Ticket views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from .models import Ticket, TicketType, PriceTier, PromoCode
from .serializers import (
    TicketSerializer, TicketListSerializer, TicketTypeSerializer,
    TicketTypeCreateSerializer, TicketTypeUpdateSerializer,
    PriceTierSerializer, PromoCodeSerializer, TicketCheckInSerializer,
    TicketTransferSerializer, TicketBulkCheckInSerializer
)
from core.permissions import IsEventOwner, CanCheckIn


class PromoCodeViewSet(viewsets.ModelViewSet):
    """Promo code viewset"""
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organization', 'event', 'is_active']
    search_fields = ['code', 'description']
    
    def get_queryset(self):
        queryset = PromoCode.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(organization__userorganizations__user=self.request.user) |
                Q(event__owner=self.request.user)
            ).distinct()
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def validate_code(self, request, pk=None):
        """Validate if promo code is valid"""
        promo_code = self.get_object()
        data = {
            'is_valid': promo_code.is_active,
            'discount_type': promo_code.discount_type,
            'discount_value': str(promo_code.discount_value),
            'remaining_uses': promo_code.remaining_uses
        }
        return Response(data)


class PriceTierViewSet(viewsets.ModelViewSet):
    """Price tier viewset"""
    serializer_class = PriceTierSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['ticket_type', 'is_active']
    ordering_fields = ['price', 'start_date', 'created_at']
    
    def get_queryset(self):
        queryset = PriceTier.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                ticket_type__event__owner=self.request.user |
                Q(ticket_type__event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset


class TicketTypeViewSet(viewsets.ModelViewSet):
    """Ticket type viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event', 'ticket_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['base_price', 'created_at', 'quantity_available']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TicketTypeCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TicketTypeUpdateSerializer
        return TicketTypeSerializer
    
    def get_queryset(self):
        queryset = TicketType.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(event__owner=self.request.user) |
                Q(event__organization__userorganizations__user=self.request.user)
            ).distinct()
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get ticket type statistics"""
        ticket_type = self.get_object()
        stats = {
            'total_quantity': ticket_type.quantity_available,
            'sold_quantity': ticket_type.quantity_available - ticket_type.available_quantity,
            'available_quantity': ticket_type.available_quantity,
            'sales_total': str(ticket_type.sales_total),
            'average_price': str(ticket_type.base_price)
        }
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def price_tiers(self, request, pk=None):
        """Get price tiers for this ticket type"""
        ticket_type = self.get_object()
        tiers = ticket_type.price_tiers.all()
        serializer = PriceTierSerializer(tiers, many=True)
        return Response(serializer.data)


class TicketViewSet(viewsets.ModelViewSet):
    """Ticket viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ticket_type', 'status', 'checkin_status']
    search_fields = ['ticket_number', 'attendee__email']
    ordering_fields = ['created_at', 'price_paid', 'ticket_number']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TicketListSerializer
        return TicketSerializer
    
    def get_queryset(self):
        queryset = Ticket.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(ticket_type__event__owner=self.request.user) |
                Q(ticket_type__event__organization__userorganizations__user=self.request.user) |
                Q(attendee__user=self.request.user)
            ).distinct()
        return queryset
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, CanCheckIn])
    def check_in(self, request, pk=None):
        """Check in a ticket"""
        ticket = self.get_object()
        
        # Check permissions
        self.check_object_permissions(request, ticket)
        
        serializer = TicketCheckInSerializer(data=request.data)
        
        if serializer.is_valid():
            ticket.checkin_status = 'checked_in'
            ticket.checked_in_at = timezone.now()
            ticket.save()
            return Response({
                'status': 'success',
                'message': 'Ticket checked in successfully',
                'ticket': TicketSerializer(ticket).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """Transfer ticket to another attendee"""
        ticket = self.get_object()
        serializer = TicketTransferSerializer(data=request.data)
        
        if serializer.is_valid():
            ticket.transfer_status = 'pending'
            ticket.transferred_to = serializer.validated_data['transferred_to']
            ticket.save()
            return Response({
                'status': 'success',
                'message': 'Ticket transfer initiated',
                'ticket': TicketSerializer(ticket).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_check_in(self, request):
        """Bulk check in multiple tickets"""
        serializer = TicketBulkCheckInSerializer(data=request.data)
        
        if serializer.is_valid():
            ticket_ids = serializer.validated_data['ticket_ids']
            checked_in_count = 0
            failed_count = 0
            
            for ticket_id in ticket_ids:
                try:
                    ticket = Ticket.objects.get(id=ticket_id)
                    ticket.checkin_status = 'checked_in'
                    ticket.checked_in_at = timezone.now()
                    ticket.save()
                    checked_in_count += 1
                except Ticket.DoesNotExist:
                    failed_count += 1
            
            return Response({
                'checked_in': checked_in_count,
                'failed': failed_count,
                'total': len(ticket_ids)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get ticket statistics"""
        queryset = self.get_queryset()
        stats = {
            'total_tickets': queryset.count(),
            'checked_in': queryset.filter(checkin_status='checked_in').count(),
            'not_checked_in': queryset.filter(checkin_status='not_checked_in').count(),
            'cancelled': queryset.filter(status='cancelled').count(),
            'total_revenue': str(queryset.aggregate(Sum('price_paid'))['price_paid__sum'] or 0)
        }
        return Response(stats)


from django.utils import timezone
