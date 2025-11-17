"""
API v1 URL Configuration
"""
from django.urls import path, include

urlpatterns = [
    # Authentication
    path('auth/', include('api.v1.auth.urls')),
    
    # Core resources
    path('users/', include('api.v1.users.urls')),
    path('organizations/', include('api.v1.organizations.urls')),
    path('events/', include('api.v1.events.urls')),
    path('tickets/', include('api.v1.tickets.urls')),
    path('orders/', include('api.v1.orders.urls')),
    path('payments/', include('api.v1.payments.urls')),
    path('attendees/', include('api.v1.attendees.urls')),
    path('files/', include('api.v1.files.urls')),
    path('notifications/', include('api.v1.notifications.urls')),
    
    # Public endpoints
    path('public/events/', include('api.v1.public_events.urls')),
    
    # Admin endpoints
    path('admin/', include('api.v1.admin.urls')),
    
    # Utility endpoints
    path('search/', include('api.v1.search.urls')),
    path('analytics/', include('api.v1.analytics.urls')),
    path('health/', include('api.v1.health.urls')),
]
