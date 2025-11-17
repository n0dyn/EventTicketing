"""
Authentication URL configuration
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from accounts.views import (
    CustomTokenObtainPairView, UserRegisterView, UserProfileView,
    PasswordChangeView, PasswordResetRequestView, PasswordResetConfirmView,
    LogoutView, current_user
)

urlpatterns = [
    # JWT Tokens
    path('login/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # User Authentication
    path('register/', UserRegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', current_user, name='current-user'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Password Management
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
