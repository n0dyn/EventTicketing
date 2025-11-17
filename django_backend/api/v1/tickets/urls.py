"""
Tickets URL configuration
"""
from django.urls import path
from django.http import JsonResponse

def placeholder_view(request):
    return JsonResponse({'message': 'Tickets API - Coming soon'})

urlpatterns = [
    path('', placeholder_view, name='tickets-list'),
]
