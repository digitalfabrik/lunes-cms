from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count

from rest_framework import viewsets

from ....cms.models import Discipline, GroupAPIKey
from ...utils import get_key
from ..serializers import DisciplineSerializer


class DisciplineViewSet(viewsets.ModelViewSet):
    """
    Retrieve disciplines, either all global disciplines or filtered by the given API key.
    Get a single record by appending the id of the requested discipline.
    """

    serializer_class = DisciplineSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of disciplines - either those created by admins or by the group of the given key

        :return: The queryset of disciplines
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Discipline.objects.none()
        queryset = Discipline.objects.filter(released=True)
        key = get_key(self.request)
        if key:
            # If the key is given, get the corresponding group
            api_key_object = GroupAPIKey.get_from_token(key)
            # Return all disciplines of the group with the given key
            self.queryset = queryset.filter(created_by=api_key_object.group)
        else:
            # If no key is given, return all admin disciplines
            self.queryset = queryset.filter(creator_is_admin=True)
        # Return annotated queryset
        return self.queryset.annotate(
            total_training_sets=Count(
                "training_sets", filter=Q(training_sets__released=True)
            ),
            total_discipline_children=Count("children"),
        )
