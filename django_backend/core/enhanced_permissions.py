"""
Enhanced permission classes for Django REST Framework
Based on 9-role RBAC system
"""

from rest_framework import permissions
from accounts.enhanced_rbac import RBACUtils, EnhancedUserRole, can_manage_user


# ============================================================================
# ROLE-BASED PERMISSION CLASSES
# ============================================================================

class IsMasterAdmin(permissions.BasePermission):
    """Allow only Master Admin"""
    message = 'Only Master Admins can access this resource.'
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == EnhancedUserRole.MASTER_ADMIN


class IsSystemAdmin(permissions.BasePermission):
    """Allow System Admin and above"""
    message = 'Only System Admins can access this resource.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in [
            EnhancedUserRole.MASTER_ADMIN,
            EnhancedUserRole.SYSTEM_ADMIN,
        ]


class IsEventOrganizerOrAbove(permissions.BasePermission):
    """Allow Event Organizer and above"""
    message = 'Only Event Organizers or higher can access this resource.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in [
            EnhancedUserRole.MASTER_ADMIN,
            EnhancedUserRole.SYSTEM_ADMIN,
            EnhancedUserRole.EVENT_ORGANIZER,
        ]


class IsCheckInStaffOrAbove(permissions.BasePermission):
    """Allow Check-In Staff and above"""
    message = 'Only Check-In Staff or higher can access this resource.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Everyone except attendees
        return request.user.role != EnhancedUserRole.ATTENDEE


# ============================================================================
# PERMISSION-BASED CLASSES
# ============================================================================

class HasPermission(permissions.BasePermission):
    """Check if user has specific permission"""
    
    def __init__(self, permission_id):
        self.permission_id = permission_id
        super().__init__()
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return RBACUtils.user_can(request.user, self.permission_id)


class CanViewEvent(permissions.BasePermission):
    """User can view event if they own it or have permission"""
    message = 'You do not have permission to view this event.'
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        if RBACUtils.user_can(request.user, 'view_all_events'):
            return True
        
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        if hasattr(obj, 'organization') and obj.organization.owner == request.user:
            return True
        
        return RBACUtils.user_can(request.user, 'view_event')


class CanEditEvent(permissions.BasePermission):
    """User can edit event if they own it and have permission"""
    message = 'You do not have permission to edit this event.'
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return RBACUtils.user_can(request.user, 'edit_event')
        
        return False


class CanCheckInAttendee(permissions.BasePermission):
    """User can check in attendee if they have permission"""
    message = 'You do not have permission to check in attendees.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return RBACUtils.user_can(request.user, 'check_in_attendee')


class CanManageUsers(permissions.BasePermission):
    """User can manage other users based on role hierarchy"""
    message = 'You cannot manage users at this level.'
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return can_manage_user(request.user, obj)


class CanManageBans(permissions.BasePermission):
    """User can manage user bans"""
    message = 'You do not have permission to manage bans.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return RBACUtils.user_can(request.user, 'manage_bans')


class CanViewAnalytics(permissions.BasePermission):
    """User can view analytics"""
    message = 'You do not have permission to view analytics.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return RBACUtils.user_can(request.user, 'view_event_metrics')


class CanIssueRefund(permissions.BasePermission):
    """User can issue refunds"""
    message = 'You do not have permission to issue refunds.'
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return RBACUtils.user_can(request.user, 'issue_refund')


# ============================================================================
# COMPOSITE PERMISSION CLASSES
# ============================================================================

class AdminOrEventOwner(permissions.BasePermission):
    """Admin or event owner"""
    message = 'You do not have permission to perform this action.'
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        if request.user.role in [EnhancedUserRole.MASTER_ADMIN, EnhancedUserRole.SYSTEM_ADMIN]:
            return True
        
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        if hasattr(obj, 'organization') and obj.organization.owner == request.user:
            return True
        
        return False


class AdminOrStaffForEvent(permissions.BasePermission):
    """Admin or staff member for the event"""
    message = 'You do not have permission to perform this action.'
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        if request.user.role in [EnhancedUserRole.MASTER_ADMIN, EnhancedUserRole.SYSTEM_ADMIN]:
            return True
        
        # Check if user is staff for this event
        if hasattr(obj, 'event'):
            event = obj.event
        else:
            event = obj
        
        if hasattr(event, 'owner') and event.owner == request.user:
            return True
        
        # Could add check for event staff membership here
        return False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_role_permissions(user):
    """Get all permissions for a user's role"""
    return RBACUtils.get_user_permissions(user)


def user_has_role(user, role):
    """Check if user has specific role"""
    if user.is_superuser:
        return True
    return user.role == role


def user_has_any_role(user, roles):
    """Check if user has any of the specified roles"""
    if user.is_superuser:
        return True
    return user.role in roles


def user_has_all_permissions(user, permission_ids):
    """Check if user has all specified permissions"""
    if user.is_superuser:
        return True
    
    user_perms = RBACUtils.get_user_permissions(user)
    return all(perm_id in user_perms for perm_id in permission_ids)


def user_has_any_permission(user, permission_ids):
    """Check if user has any of the specified permissions"""
    if user.is_superuser:
        return True
    
    user_perms = RBACUtils.get_user_permissions(user)
    return any(perm_id in user_perms for perm_id in permission_ids)

