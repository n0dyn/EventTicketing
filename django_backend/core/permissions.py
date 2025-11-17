"""
Custom permission classes for Django REST Framework
"""
from rest_framework import permissions
from django.db.models import Q


class IsOrganizer(permissions.BasePermission):
    """
    Permission check for organization members.
    User must be a member of the organization they're accessing.
    """
    message = "You are not a member of this organization."

    def has_object_permission(self, request, view, obj):
        # Check if user is member of this organization
        if hasattr(obj, 'organization'):
            return obj.organization.userorganizations.filter(
                user=request.user
            ).exists()
        elif hasattr(obj, 'userorganizations'):
            # obj is Organization itself
            return obj.userorganizations.filter(
                user=request.user
            ).exists()
        return False


class IsEventOwner(permissions.BasePermission):
    """
    Permission check for event ownership.
    User must be the event owner OR member of organizing organization.
    """
    message = "You don't have permission to access this event."

    def has_object_permission(self, request, view, obj):
        # Check if user owns the event
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        # Check if user is member of organizing organization
        if hasattr(obj, 'organization'):
            return obj.organization.userorganizations.filter(
                user=request.user
            ).exists()
        
        # For nested objects, check the event
        if hasattr(obj, 'event'):
            event = obj.event
            if event.owner == request.user:
                return True
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        # For ticket types, check through event
        if hasattr(obj, 'ticket_type') and hasattr(obj.ticket_type, 'event'):
            event = obj.ticket_type.event
            if event.owner == request.user:
                return True
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False


class IsEventOrganizerOrReadOnly(permissions.BasePermission):
    """
    Permission for event endpoints.
    - Allow any authenticated user to read
    - Only event organizers can write
    """
    
    def has_permission(self, request, view):
        # Read permissions allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write permissions only for organizers
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to event owner or organization members
        if hasattr(obj, 'owner'):
            if obj.owner == request.user:
                return True
        
        if hasattr(obj, 'organization'):
            return obj.organization.userorganizations.filter(
                user=request.user
            ).exists()
        
        return False


class IsAdmin(permissions.BasePermission):
    """
    Admin-only permission.
    User must be staff/admin.
    """
    message = "You must be an administrator to access this resource."

    def has_permission(self, request, view):
        return request.user and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_staff


class IsAccountOwner(permissions.BasePermission):
    """
    Permission for user account endpoints.
    Users can only access their own account.
    """
    message = "You can only access your own account."

    def has_object_permission(self, request, view, obj):
        # User can access their own profile
        if hasattr(obj, 'id'):
            return obj.id == request.user.id
        return False


class IsOrderOwner(permissions.BasePermission):
    """
    Permission for order endpoints.
    Users can only access their own orders.
    Organizers can access orders for their events.
    """
    message = "You don't have permission to access this order."

    def has_object_permission(self, request, view, obj):
        # User owns the order
        if hasattr(obj, 'buyer') and obj.buyer == request.user:
            return True
        
        # User is organizer of the event
        if hasattr(obj, 'event'):
            event = obj.event
            if event.owner == request.user:
                return True
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False


class IsPaymentRecipientOrAdmin(permissions.BasePermission):
    """
    Permission for payment endpoints.
    Users can access their own payments.
    Admins can access all.
    """
    message = "You don't have permission to access this payment."

    def has_object_permission(self, request, view, obj):
        # Admin can access all
        if request.user.is_staff:
            return True
        
        # User can access their own payment
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # User can access payment for their order
        if hasattr(obj, 'order') and hasattr(obj.order, 'buyer'):
            if obj.order.buyer == request.user:
                return True
        
        return False


class IsAttendeeOrEventOrganizer(permissions.BasePermission):
    """
    Permission for attendee endpoints.
    Attendees can access their own profile.
    Event organizers can access all attendees for their events.
    """
    message = "You don't have permission to access this attendee."

    def has_object_permission(self, request, view, obj):
        # User is the attendee
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # User is organizer of the event
        if hasattr(obj, 'event'):
            event = obj.event
            if event.owner == request.user:
                return True
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False


class IsOrganizationMember(permissions.BasePermission):
    """
    Generic permission for organization resources.
    User must be member of the organization.
    """
    message = "You are not a member of this organization."

    def has_permission(self, request, view):
        # Allow authenticated users to try (will be filtered by queryset)
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check various ways object might be related to organization
        if hasattr(obj, 'organization'):
            org = obj.organization
        elif hasattr(obj, 'event') and hasattr(obj.event, 'organization'):
            org = obj.event.organization
        elif hasattr(obj, 'userorganizations'):
            org = obj  # obj is the organization
        else:
            return False
        
        if org is None:
            return True  # Allow if no organization restriction
        
        return org.userorganizations.filter(user=request.user).exists()


class CanManageWaitlist(permissions.BasePermission):
    """
    Permission for waitlist management.
    Only event organizers can manage waitlists.
    """
    message = "You don't have permission to manage this waitlist."

    def has_object_permission(self, request, view, obj):
        # Get the event from the waitlist
        if hasattr(obj, 'event'):
            event = obj.event
            
            # Check if user owns the event
            if event.owner == request.user:
                return True
            
            # Check if user is member of organizing organization
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False


class CanCheckIn(permissions.BasePermission):
    """
    Permission for check-in operations.
    Only event staff and organizers can check in attendees.
    """
    message = "You don't have permission to check in attendees."

    def has_object_permission(self, request, view, obj):
        # Get the event from the check-in
        if hasattr(obj, 'ticket'):
            event = obj.ticket.ticket_type.event
            
            # Check if user owns the event
            if event.owner == request.user:
                return True
            
            # Check if user is member of organizing organization
            if event.organization:
                return event.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False


class CanManageFiles(permissions.BasePermission):
    """
    Permission for file management.
    Users can manage files in their organizations.
    """
    message = "You don't have permission to manage this file."

    def has_object_permission(self, request, view, obj):
        # Check if user uploaded the file
        if hasattr(obj, 'uploaded_by') and obj.uploaded_by == request.user:
            return True
        
        # Check if user is member of the organization
        if hasattr(obj, 'organization'):
            if obj.organization:
                return obj.organization.userorganizations.filter(
                    user=request.user
                ).exists()
        
        return False

