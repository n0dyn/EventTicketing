"""
Organizations URL configuration
"""
from django.urls import path
from organizations.views import (
    OrganizationListCreateView, OrganizationDetailView,
    my_organizations, organization_stats
)

urlpatterns = [
    path('', OrganizationListCreateView.as_view(), name='organization-list'),
    path('my/', my_organizations, name='my-organizations'),
    path('<uuid:pk>/', OrganizationDetailView.as_view(), name='organization-detail'),
    path('<uuid:pk>/stats/', organization_stats, name='organization-stats'),
]
