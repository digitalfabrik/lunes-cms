from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.timezone import now

from rest_framework import permissions

from ..cms.models import GroupAPIKey
from .utils import get_key


class VerifyGroupKey(permissions.AllowAny):
    """Simple permissions class that blocks
    requests if no valid API-Token is delivered.
    Inherits from `permissions.AllowAny`.
    """

    def has_permission(self, request, view):
        """Checks whether a valid API-Key is send
        by the user in the authorization header

        :param request: http request
        :type request: HttpRequest
        :param view: restframework view
        :type view: viewsets.ModelViewSet
        :return: False if user doesn't send a API-key
        :rtype: bool
        """
        key = get_key(request)
        if key is None:
            return False
        GroupAPIKey.get_from_token(key)
        return True
