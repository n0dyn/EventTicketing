"""
public_events URL configuration
"""
from django.urls import path
from django.http import JsonResponse

def placeholder_view(request):
    return JsonResponse({'message': 'public_events API - Coming soon'})

urlpatterns = [
    path('', placeholder_view, name='public_events-list'),
]
