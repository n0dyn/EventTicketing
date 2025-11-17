"""
Enhanced Role-Based Access Control (RBAC) System
9 distinct roles with granular permissions
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
import json

User = get_user_model()


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

class EnhancedUserRole(models.TextChoices):
    """Enhanced user roles for the system"""
    
    # System Level
    MASTER_ADMIN = 'master_admin', _('Master Admin - Complete System Access')
    SYSTEM_ADMIN = 'system_admin', _('System Admin - All Events Management')
    
    # Event Level
    EVENT_ORGANIZER = 'event_organizer', _('Event Organizer - Full Event Control')
    EVENT_MANAGER = 'event_manager', _('Event Manager - Ticket & Order Management')
    MARKETING_MANAGER = 'marketing_manager', _('Marketing Manager - Promotions & Analytics')
    
    # Staff Level
    CHECK_IN_STAFF = 'check_in_staff', _('Check-In Staff - QR Scanning Only')
    GATE_SUPERVISOR = 'gate_supervisor', _('Gate Supervisor - Gate Management')
    TICKET_SUPPORT = 'ticket_support', _('Ticket Support - Customer Support')
    
    # Attendee Level
    ATTENDEE = 'attendee', _('Attendee - Standard Ticket Holder')


# ============================================================================
# PERMISSION DEFINITIONS
# ============================================================================

class PermissionCategory(models.TextChoices):
    """Permission categories for organization"""
    EVENT_MANAGEMENT = 'event_management', _('Event Management')
    TICKET_MANAGEMENT = 'ticket_management', _('Ticket Management')
    ATTENDEE_MANAGEMENT = 'attendee_management', _('Attendee Management')
    PAYMENT_MANAGEMENT = 'payment_management', _('Payment Management')
    ANALYTICS = 'analytics', _('Analytics & Reporting')
    STAFF_MANAGEMENT = 'staff_management', _('Staff Management')
    SECURITY = 'security', _('Security & Compliance')
    SYSTEM_ADMIN = 'system_admin', _('System Administration')


class Permission(models.Model):
    """
    Granular permission model
    Defines what can be done in the system
    """
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=PermissionCategory.choices,
        default=PermissionCategory.EVENT_MANAGEMENT
    )
    
    class Meta:
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
    
    def __str__(self):
        return f"{self.name} ({self.id})"


class RolePermissionMatrix(models.Model):
    """
    Maps roles to permissions
    Defines what each role can do
    """
    role = models.CharField(
        max_length=50,
        choices=EnhancedUserRole.choices,
        unique=True
    )
    permissions = models.ManyToManyField(Permission, related_name='roles')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Role Permission Matrix'
        verbose_name_plural = 'Role Permission Matrices'
    
    def __str__(self):
        return f"Permissions for {self.role}"
    
    @classmethod
    def get_role_permissions(cls, role):
        """Get all permissions for a role"""
        try:
            matrix = cls.objects.get(role=role)
            return set(matrix.permissions.values_list('id', flat=True))
        except cls.DoesNotExist:
            return set()
    
    @classmethod
    def user_has_permission(cls, user, permission_id):
        """Check if user has a specific permission"""
        if user.is_superuser:
            return True
        
        try:
            role = user.role
            permissions = cls.get_role_permissions(role)
            return permission_id in permissions
        except:
            return False


class UserPermissionOverride(models.Model):
    """
    Allow granting additional permissions to specific users
    Useful for exceptions and special cases
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permission_override')
    additional_permissions = models.ManyToManyField(Permission, related_name='user_overrides')
    
    # Metadata
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_overrides'
    )
    reason = models.TextField(help_text='Reason for granting additional permissions')
    expires_at = models.DateTimeField(null=True, blank=True, help_text='When override expires (null = permanent)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Permission Override'
        verbose_name_plural = 'User Permission Overrides'
    
    def __str__(self):
        return f"Override for {self.user.email}"
    
    @property
    def is_active(self):
        """Check if override is currently active"""
        if not self.expires_at:
            return True
        from django.utils import timezone
        return timezone.now() <= self.expires_at


# ============================================================================
# PERMISSION DEFINITIONS - DETAILED
# ============================================================================

MASTER_ADMIN_PERMISSIONS = {
    'event_management': [
        'create_event',
        'edit_event',
        'delete_event',
        'publish_event',
        'cancel_event',
    ],
    'ticket_management': [
        'create_ticket_type',
        'edit_ticket_type',
        'delete_ticket_type',
        'disable_ticket',
        'blacklist_ticket',
        're_enable_ticket',
    ],
    'attendee_management': [
        'check_in_attendee',
        'check_out_attendee',
        'ban_user',
        'lift_ban',
        'view_attendees',
        'export_attendees',
    ],
    'payment_management': [
        'process_payment',
        'issue_refund',
        'view_payments',
        'manage_payment_methods',
    ],
    'analytics': [
        'view_event_metrics',
        'view_location_metrics',
        'view_revenue_analytics',
        'view_attendance_analytics',
        'export_analytics',
    ],
    'staff_management': [
        'create_staff',
        'edit_staff',
        'delete_staff',
        'assign_roles',
        'manage_permissions',
    ],
    'security': [
        'view_audit_logs',
        'manage_bans',
        'manage_blacklists',
        'view_fraud_alerts',
    ],
    'system_admin': [
        'manage_system_settings',
        'manage_database',
        'view_system_logs',
        'manage_backups',
    ],
}

SYSTEM_ADMIN_PERMISSIONS = {
    'event_management': [
        'view_event',
        'view_all_events',
    ],
    'attendee_management': [
        'view_attendees',
        'ban_user',
        'lift_ban',
    ],
    'analytics': [
        'view_event_metrics',
        'view_location_metrics',
        'export_analytics',
    ],
    'staff_management': [
        'view_staff',
        'manage_permissions',
    ],
    'security': [
        'view_audit_logs',
        'manage_bans',
    ],
}

EVENT_ORGANIZER_PERMISSIONS = {
    'event_management': [
        'create_event',
        'edit_event',
        'publish_event',
        'cancel_event',
        'view_event',
        'delete_event',
    ],
    'ticket_management': [
        'create_ticket_type',
        'edit_ticket_type',
        'delete_ticket_type',
        'disable_ticket',
        'blacklist_ticket',
    ],
    'attendee_management': [
        'check_in_attendee',
        'ban_user',
        'view_attendees',
        'export_attendees',
    ],
    'payment_management': [
        'process_payment',
        'issue_refund',
        'view_payments',
    ],
    'analytics': [
        'view_event_metrics',
        'view_location_metrics',
        'view_revenue_analytics',
        'view_attendance_analytics',
        'export_analytics',
    ],
    'staff_management': [
        'create_staff',
        'edit_staff',
        'assign_roles',
    ],
    'security': [
        'view_audit_logs',
        'manage_bans',
        'manage_blacklists',
    ],
}

EVENT_MANAGER_PERMISSIONS = {
    'event_management': [
        'view_event',
    ],
    'ticket_management': [
        'view_ticket_types',
        'disable_ticket',
    ],
    'attendee_management': [
        'check_in_attendee',
        'view_attendees',
    ],
    'payment_management': [
        'view_payments',
    ],
    'analytics': [
        'view_event_metrics',
    ],
}

MARKETING_MANAGER_PERMISSIONS = {
    'event_management': [
        'view_event',
    ],
    'ticket_management': [
        'view_ticket_types',
    ],
    'analytics': [
        'view_event_metrics',
        'view_location_metrics',
        'view_revenue_analytics',
        'view_attendance_analytics',
        'export_analytics',
    ],
}

CHECK_IN_STAFF_PERMISSIONS = {
    'attendee_management': [
        'check_in_attendee',
        'check_out_attendee',
    ],
}

GATE_SUPERVISOR_PERMISSIONS = {
    'event_management': [
        'view_event',
    ],
    'attendee_management': [
        'check_in_attendee',
        'check_out_attendee',
        'view_attendees',
    ],
    'analytics': [
        'view_location_metrics',
    ],
}

TICKET_SUPPORT_PERMISSIONS = {
    'ticket_management': [
        'view_ticket_types',
    ],
    'attendee_management': [
        'view_attendees',
    ],
    'payment_management': [
        'view_payments',
    ],
}

ATTENDEE_PERMISSIONS = {
    'ticket_management': [
        'view_own_tickets',
        'transfer_ticket',
    ],
}

# Permission mapping by role
ROLE_PERMISSION_MAP = {
    EnhancedUserRole.MASTER_ADMIN: MASTER_ADMIN_PERMISSIONS,
    EnhancedUserRole.SYSTEM_ADMIN: SYSTEM_ADMIN_PERMISSIONS,
    EnhancedUserRole.EVENT_ORGANIZER: EVENT_ORGANIZER_PERMISSIONS,
    EnhancedUserRole.EVENT_MANAGER: EVENT_MANAGER_PERMISSIONS,
    EnhancedUserRole.MARKETING_MANAGER: MARKETING_MANAGER_PERMISSIONS,
    EnhancedUserRole.CHECK_IN_STAFF: CHECK_IN_STAFF_PERMISSIONS,
    EnhancedUserRole.GATE_SUPERVISOR: GATE_SUPERVISOR_PERMISSIONS,
    EnhancedUserRole.TICKET_SUPPORT: TICKET_SUPPORT_PERMISSIONS,
    EnhancedUserRole.ATTENDEE: ATTENDEE_PERMISSIONS,
}


# ============================================================================
# ROLE-BASED ACCESS CONTROL UTILITIES
# ============================================================================

class RBACUtils:
    """Utility functions for RBAC operations"""
    
    @staticmethod
    def initialize_roles():
        """Initialize all roles and permissions"""
        # Create all permissions
        all_permissions = {}
        
        for role_perms in ROLE_PERMISSION_MAP.values():
            for category, perms in role_perms.items():
                for perm in perms:
                    if perm not in all_permissions:
                        all_permissions[perm] = category
        
        # Create Permission objects
        for perm_id, category in all_permissions.items():
            Permission.objects.get_or_create(
                id=perm_id,
                defaults={
                    'name': perm_id.replace('_', ' ').title(),
                    'description': f'Permission to {perm_id.replace("_", " ")}',
                    'category': category,
                }
            )
        
        # Create RolePermissionMatrix entries
        for role, perms_by_category in ROLE_PERMISSION_MAP.items():
            matrix, created = RolePermissionMatrix.objects.get_or_create(role=role)
            
            # Add permissions to matrix
            perm_ids = []
            for category, perms in perms_by_category.items():
                perm_ids.extend(perms)
            
            perm_objects = Permission.objects.filter(id__in=perm_ids)
            matrix.permissions.set(perm_objects)
    
    @staticmethod
    def get_user_permissions(user):
        """Get all permissions for a user (including overrides)"""
        if user.is_superuser:
            return set(Permission.objects.values_list('id', flat=True))
        
        # Get role-based permissions
        permissions = RolePermissionMatrix.get_role_permissions(user.role)
        
        # Add override permissions if they exist
        try:
            override = UserPermissionOverride.objects.get(user=user)
            if override.is_active:
                override_perms = set(override.additional_permissions.values_list('id', flat=True))
                permissions.update(override_perms)
        except UserPermissionOverride.DoesNotExist:
            pass
        
        return permissions
    
    @staticmethod
    def user_can(user, permission_id):
        """Check if user can perform an action"""
        if user.is_superuser:
            return True
        
        permissions = RBACUtils.get_user_permissions(user)
        return permission_id in permissions
    
    @staticmethod
    def get_role_display_name(role):
        """Get display name for a role"""
        return dict(EnhancedUserRole.choices).get(role, role)
    
    @staticmethod
    def get_role_description(role):
        """Get description for a role"""
        descriptions = {
            EnhancedUserRole.MASTER_ADMIN: 'Complete system access. Can manage everything including system settings.',
            EnhancedUserRole.SYSTEM_ADMIN: 'Can manage all events and system-wide operations. Limited system admin access.',
            EnhancedUserRole.EVENT_ORGANIZER: 'Full control over their events. Can create, edit, manage staff and view analytics.',
            EnhancedUserRole.EVENT_MANAGER: 'Can manage tickets and attendees for assigned events.',
            EnhancedUserRole.MARKETING_MANAGER: 'Can view promotions, analytics, and create marketing campaigns.',
            EnhancedUserRole.CHECK_IN_STAFF: 'Can scan QR codes and check in attendees. Most restricted access.',
            EnhancedUserRole.GATE_SUPERVISOR: 'Can manage gate operations, capacity, and view real-time metrics.',
            EnhancedUserRole.TICKET_SUPPORT: 'Can handle customer support for tickets and payments.',
            EnhancedUserRole.ATTENDEE: 'Can purchase tickets and view their own information.',
        }
        return descriptions.get(role, 'Unknown role')


# ============================================================================
# PERMISSION HIERARCHY
# ============================================================================

PERMISSION_HIERARCHY = {
    # Top level (most permissive)
    EnhancedUserRole.MASTER_ADMIN: 1,
    EnhancedUserRole.SYSTEM_ADMIN: 2,
    EnhancedUserRole.EVENT_ORGANIZER: 3,
    EnhancedUserRole.EVENT_MANAGER: 4,
    EnhancedUserRole.MARKETING_MANAGER: 5,
    EnhancedUserRole.GATE_SUPERVISOR: 6,
    EnhancedUserRole.TICKET_SUPPORT: 7,
    EnhancedUserRole.CHECK_IN_STAFF: 8,
    EnhancedUserRole.ATTENDEE: 9,
    # Bottom level (most restrictive)
}


def can_manage_user(manager_user, target_user):
    """Check if manager_user can manage target_user"""
    if manager_user.is_superuser:
        return True
    
    manager_level = PERMISSION_HIERARCHY.get(manager_user.role, 100)
    target_level = PERMISSION_HIERARCHY.get(target_user.role, 100)
    
    return manager_level < target_level

