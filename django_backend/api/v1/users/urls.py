"""
Users URL configuration
"""
from django.urls import path
from accounts.views import (
    UserListCreateView, UserDetailView, UserProfileView,
    UserRegistrationView
)

urlpatterns = [
    path('', UserListCreateView.as_view(), name='user-list'),
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
]
