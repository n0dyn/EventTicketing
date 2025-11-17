"""
Events URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from events.views import (
    EventCategoryListCreateView, EventCategoryDetailView,
    EventViewSet, EventSeriesViewSet, RecurrencePatternViewSet,
    EventInstanceViewSet, public_events, event_stats
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'events', EventViewSet)
router.register(r'series', EventSeriesViewSet)
router.register(r'recurrence-patterns', RecurrencePatternViewSet)
router.register(r'instances', EventInstanceViewSet)

urlpatterns = [
    # Categories
    path('categories/', EventCategoryListCreateView.as_view(), name='event-category-list'),
    path('categories/<uuid:pk>/', EventCategoryDetailView.as_view(), name='event-category-detail'),
    
    # Public events
    path('public/', public_events, name='public-events'),
    
    # Event stats
    path('events/<uuid:pk>/stats/', event_stats, name='event-stats'),
    
    # Include router URLs
    path('', include(router.urls)),
]
