from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from rest_framework import viewsets

from ....cms.models import GroupAPIKey, TrainingSet
from ...permissions import VerifyGroupKey
from ...utils import get_key
from ..serializers import GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    List available information of a user group.
    A valid API-Key is required.
    There is no need to pass a group id or similar,
    the returned queryset is filtered by the delivered API-Key.
    """

    permission_classes = [VerifyGroupKey]
    serializer_class = GroupSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`GroupViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return TrainingSet.objects.none()
        key = get_key(self.request)
        if not key:
            raise PermissionDenied()
        try:
            api_key_object = GroupAPIKey.get_from_token(key)
        except GroupAPIKey.DoesNotExist:
            raise PermissionDenied()
        if not api_key_object:
            raise PermissionDenied()
        queryset = Group.objects.filter(id=api_key_object.group_id)
        return queryset
