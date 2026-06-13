# Central module for custom permission checks across all apps.
# Add new permission helper functions here as the project grows.
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin


def can_view_analytics(user: AbstractBaseUser | PermissionsMixin) -> bool:
    """Return True for superusers and users with the can_view_analytics permission."""
    return user.has_perm("analytics.can_view_analytics")
