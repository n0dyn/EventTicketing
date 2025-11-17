"""
EventTicketing URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def api_root(request):
    """API root endpoint"""
    return JsonResponse({
        "message": "Welcome to EventTicketing API",
        "version": "1.0.0",
        "status": "healthy"
    })

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        "status": "healthy",
        "service": "EventTicketing API",
        "timestamp": "2025-01-06T16:00:00Z"
    })

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Root
    path('', api_root, name='api-root'),
    path('health/', health_check, name='health-check'),
    
    # API v1
    path('api/v1/', include('api.v1.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)