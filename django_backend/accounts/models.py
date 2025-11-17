from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class UserRole(models.TextChoices):
    """Enum for user roles in the system"""
    ADMIN = 'admin', 'Admin'
    ORGANIZER = 'organizer', 'Organizer'
    ATTENDEE = 'attendee', 'Attendee'


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.ATTENDEE
    )
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return the user's full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the user's first name"""
        return self.first_name


class UserOrganization(models.Model):
    """
    Through model for User-Organization many-to-many relationship
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_organizations'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='user_organizations'
    )
    role = models.CharField(max_length=50, default='member')
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['user', 'organization']
        verbose_name = 'User Organization'
        verbose_name_plural = 'User Organizations'

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"
