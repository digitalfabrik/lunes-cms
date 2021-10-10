from django.contrib.auth.models import Group
from rest_framework import viewsets
from vocgui.models import TrainingSet
from vocgui.serializers import GroupSerializer
from vocgui.permissions import VerifyGroupKey
from vocgui.models import GroupAPIKey
from vocgui.utils import get_key
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from .utils import check_group_object_permissions


class GroupViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Group module.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
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
        check_group_object_permissions(self.request, self.kwargs["group_id"])
        queryset = Group.objects.filter(id=self.kwargs["group_id"])
        return queryset
