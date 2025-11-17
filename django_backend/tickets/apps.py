"""
Django app configuration for tickets application
"""

from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Configuration for tickets app"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'
    verbose_name = 'Ticketing System'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signals to register them
        try:
            from . import ticket_enhancement_signals
        except ImportError:
            pass
        
        # Initialize RBAC on first run
        try:
            from accounts.enhanced_rbac import RBACUtils
            # This will create permissions and role matrices if they don't exist
            # Uncomment in production to auto-initialize:
            # if not RolePermissionMatrix.objects.exists():
            #     RBACUtils.initialize_roles()
        except Exception:
            pass
