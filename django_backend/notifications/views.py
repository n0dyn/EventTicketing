"""
Notification views for Django REST Framework
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import (
    EmailTemplate, NotificationTemplate, Notification,
    NotificationPreference, NotificationCampaign
)
from .serializers import (
    EmailTemplateSerializer, EmailTemplateCreateSerializer,
    NotificationTemplateSerializer, NotificationTemplateCreateSerializer,
    NotificationSerializer, NotificationListSerializer,
    NotificationPreferenceSerializer, NotificationPreferenceUpdateSerializer,
    NotificationCampaignSerializer, NotificationCampaignCreateSerializer,
    NotificationCampaignLaunchSerializer, NotificationSendSerializer
)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """Email template viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organization', 'is_default', 'is_active']
    search_fields = ['name', 'subject']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmailTemplateCreateSerializer
        return EmailTemplateSerializer
    
    def get_queryset(self):
        queryset = EmailTemplate.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(organization__userorganizations__user=self.request.user) |
                Q(is_default=True)
            ).distinct()
        return queryset


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """Notification template viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organization', 'template_type', 'trigger_event', 'is_active']
    search_fields = ['name']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationTemplateCreateSerializer
        return NotificationTemplateSerializer
    
    def get_queryset(self):
        queryset = NotificationTemplate.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                organization__userorganizations__user=self.request.user
            ).distinct()
        return queryset


class NotificationViewSet(viewsets.ModelViewSet):
    """Notification viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'channel', 'recipient', 'read_at']
    search_fields = ['subject', 'body']
    ordering_fields = ['created_at', 'sent_at', 'read_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        queryset = Notification.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(recipient=self.request.user)
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save()
        
        return Response({
            'status': 'success',
            'notification': NotificationSerializer(notification).data
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for current user"""
        queryset = self.get_queryset().filter(read_at__isnull=True)
        updated = queryset.update(read_at=timezone.now())
        
        return Response({
            'status': 'success',
            'updated': updated
        })
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send notification to users"""
        serializer = NotificationSendSerializer(data=request.data)
        
        if serializer.is_valid():
            recipient_ids = serializer.validated_data['recipient_ids']
            subject = serializer.validated_data['subject']
            body = serializer.validated_data['body']
            channel = serializer.validated_data['channel']
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            sent_count = 0
            failed_count = 0
            
            for user_id in recipient_ids:
                try:
                    user = User.objects.get(id=user_id)
                    Notification.objects.create(
                        recipient=user,
                        subject=subject,
                        body=body,
                        channel=channel,
                        status='sent'
                    )
                    sent_count += 1
                except User.DoesNotExist:
                    failed_count += 1
            
            return Response({
                'status': 'success',
                'sent': sent_count,
                'failed': failed_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        unread = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({'unread_count': unread})


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """Notification preference viewset"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def list(self, request):
        """Get notification preferences"""
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update(self, request):
        """Update notification preferences"""
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceUpdateSerializer(
            preference,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'preference': NotificationPreferenceSerializer(preference).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationCampaignViewSet(viewsets.ModelViewSet):
    """Notification campaign viewset"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['organization', 'event', 'status', 'channel']
    search_fields = ['name', 'subject']
    ordering_fields = ['created_at', 'scheduled_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotificationCampaignCreateSerializer
        return NotificationCampaignSerializer
    
    def get_queryset(self):
        queryset = NotificationCampaign.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                organization__userorganizations__user=self.request.user
            ).distinct()
        return queryset
    
    @action(detail=True, methods=['post'])
    def launch(self, request, pk=None):
        """Launch a campaign"""
        campaign = self.get_object()
        serializer = NotificationCampaignLaunchSerializer(data=request.data)
        
        if serializer.is_valid():
            if campaign.status != 'draft':
                return Response(
                    {'error': 'Only draft campaigns can be launched'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recipient users based on filter
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if campaign.recipient_filter:
                # Apply filter logic
                if campaign.recipient_filter == 'all_attendees':
                    if campaign.event:
                        from attendees.models import Attendee
                        recipients = User.objects.filter(
                            attendees__event=campaign.event
                        ).distinct()
                    else:
                        recipients = User.objects.all()
                else:
                    recipients = User.objects.all()
            else:
                recipients = User.objects.all()
            
            # Send notifications
            for recipient in recipients:
                Notification.objects.create(
                    recipient=recipient,
                    template=None,
                    subject=campaign.subject,
                    body=campaign.message,
                    channel=campaign.channel,
                    status='sent'
                )
            
            campaign.status = 'sent'
            campaign.sent_at = timezone.now()
            campaign.save()
            
            return Response({
                'status': 'success',
                'campaign': NotificationCampaignSerializer(campaign).data,
                'recipients': recipients.count()
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a campaign"""
        campaign = self.get_object()
        
        if campaign.status not in ['draft', 'scheduled']:
            return Response(
                {'error': 'Only draft or scheduled campaigns can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        campaign.status = 'cancelled'
        campaign.save()
        
        return Response({
            'status': 'success',
            'campaign': NotificationCampaignSerializer(campaign).data
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get campaign statistics"""
        campaign = self.get_object()
        stats = {
            'total_sent': campaign.notifications.count(),
            'delivered': campaign.notifications.filter(status='sent').count(),
            'failed': campaign.notifications.filter(status='failed').count(),
            'read_rate': 0
        }
        
        if stats['delivered'] > 0:
            read = campaign.notifications.filter(read_at__isnull=False).count()
            stats['read_rate'] = round((read / stats['delivered']) * 100, 2)
        
        return Response(stats)
