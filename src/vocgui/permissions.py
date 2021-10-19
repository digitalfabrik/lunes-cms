from typing import get_args
from rest_framework_api_key.permissions import BaseHasAPIKey
from .models import GroupAPIKey
from rest_framework import permissions
from rest_framework_api_key.models import APIKey
from django.contrib.auth.models import Group
from django.db.models import Q
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
        :param view: [description]
        :type view: typing.Any
        :return: False if user doesn't send a API-key
        :rtype: bool
        """
        key = get_key(request)
        if key is None:
            return False
        api_key = GroupAPIKey.objects.get_from_key(key)
        return True
