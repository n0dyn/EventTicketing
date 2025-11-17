"""
URL configuration for ticketing system enhancements
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tickets.ticket_enhancement_views import (
    TicketDisablementViewSet, TicketBlacklistViewSet,
    UserBanViewSet, TicketTransferViewSet,
    EventMetricsViewSet, LocationMetricsViewSet
)

router = DefaultRouter()

# Register routers
router.register(r'blacklist', TicketBlacklistViewSet, basename='ticket-blacklist')

urlpatterns = [
    # Ticket-specific endpoints
    path(
        'tickets/<uuid:ticket_id>/disablements/',
        TicketDisablementViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='ticket-disablements'
    ),
    path(
        'tickets/<uuid:ticket_id>/disablements/<uuid:pk>/',
        TicketDisablementViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update'
        }),
        name='ticket-disablement-detail'
    ),
    path(
        'tickets/<uuid:ticket_id>/disablements/<uuid:pk>/re-enable/',
        TicketDisablementViewSet.as_view({'post': 're_enable'}),
        name='ticket-disablement-re-enable'
    ),
    
    # Ticket transfer endpoints
    path(
        'tickets/<uuid:ticket_id>/transfers/',
        TicketTransferViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='ticket-transfers'
    ),
    path(
        'tickets/<uuid:ticket_id>/transfers/<uuid:pk>/',
        TicketTransferViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update'
        }),
        name='ticket-transfer-detail'
    ),
    path(
        'tickets/<uuid:ticket_id>/transfers/<uuid:pk>/accept/',
        TicketTransferViewSet.as_view({'post': 'accept'}),
        name='ticket-transfer-accept'
    ),
    path(
        'tickets/<uuid:ticket_id>/transfers/<uuid:pk>/decline/',
        TicketTransferViewSet.as_view({'post': 'decline'}),
        name='ticket-transfer-decline'
    ),
    
    # User ban endpoints
    path(
        'users/<uuid:user_id>/bans/',
        UserBanViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='user-bans'
    ),
    path(
        'users/<uuid:user_id>/bans/<uuid:pk>/',
        UserBanViewSet.as_view({
            'get': 'retrieve',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='user-ban-detail'
    ),
    path(
        'users/<uuid:user_id>/bans/<uuid:pk>/request-appeal/',
        UserBanViewSet.as_view({'post': 'request_appeal'}),
        name='user-ban-request-appeal'
    ),
    path(
        'users/<uuid:user_id>/bans/<uuid:pk>/approve-appeal/',
        UserBanViewSet.as_view({'post': 'approve_appeal'}),
        name='user-ban-approve-appeal'
    ),
    path(
        'users/<uuid:user_id>/bans/<uuid:pk>/reject-appeal/',
        UserBanViewSet.as_view({'post': 'reject_appeal'}),
        name='user-ban-reject-appeal'
    ),
    path(
        'users/<uuid:user_id>/bans/<uuid:pk>/lift/',
        UserBanViewSet.as_view({'post': 'lift'}),
        name='user-ban-lift'
    ),
    
    # Event metrics endpoints
    path(
        'events/<uuid:event_id>/metrics/',
        EventMetricsViewSet.as_view({'get': 'retrieve'}),
        name='event-metrics'
    ),
    
    # Location metrics endpoints
    path(
        'events/<uuid:event_id>/location-metrics/',
        LocationMetricsViewSet.as_view({'get': 'list'}),
        name='event-location-metrics'
    ),
    path(
        'events/<uuid:event_id>/location-metrics/<uuid:pk>/',
        LocationMetricsViewSet.as_view({'get': 'retrieve'}),
        name='event-location-metrics-detail'
    ),
    path(
        'events/<uuid:event_id>/location-metrics/today/',
        LocationMetricsViewSet.as_view({'get': 'today'}),
        name='event-location-metrics-today'
    ),
    path(
        'events/<uuid:event_id>/location-metrics/hourly/',
        LocationMetricsViewSet.as_view({'get': 'hourly'}),
        name='event-location-metrics-hourly'
    ),
    
    # Blacklist check endpoint
    path(
        'tickets/check-blacklist/',
        TicketBlacklistViewSet.as_view({'post': 'check_ticket'}),
        name='check-ticket-blacklist'
    ),
    
    # Include router URLs
    path('', include(router.urls)),
]

