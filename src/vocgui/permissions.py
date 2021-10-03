from typing import get_args
from rest_framework_api_key.permissions import BaseHasAPIKey
from .models import GroupAPIKey
from rest_framework import permissions

class VerifyGroupKey(permissions.AllowAny):
    def get_key(self, request):
        if request.META.get("HTTP_AUTHORIZATION"):
            return True
        else:
            return False

    def has_permission(self, request, view):
        return self.get_key(request)

    def has_object_permission(self, request, view, obj):
        return self.get_key(request)