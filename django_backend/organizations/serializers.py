"""
Organization serializers for Django REST Framework
"""
from rest_framework import serializers
from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    """Organization serializer"""
    member_count = serializers.ReadOnlyField()
    event_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'description', 'website', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'logo', 'is_active', 'created_at', 'updated_at',
            'member_count', 'event_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'member_count', 'event_count']


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Organization creation serializer"""
    
    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'website', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'logo'
        ]


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Organization update serializer"""
    
    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'website', 'email', 'phone',
            'address', 'city', 'state', 'country', 'postal_code',
            'logo', 'is_active'
        ]


class OrganizationListSerializer(serializers.ModelSerializer):
    """Organization list serializer (minimal fields)"""
    member_count = serializers.ReadOnlyField()
    event_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'description', 'website', 'email',
            'is_active', 'created_at', 'member_count', 'event_count'
        ]
