from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from ..matomo_tracking import matomo_tracking
from ..serializers import UnitWordRelationSerializer
from ....cmsv2.models import Unit
from ....cmsv2.models.unit import UnitWordRelation


class UnitWordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words that belong to a given unit
    """

    serializer_class = UnitWordRelationSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All words of unit", resource_id="unit_id")
    def list(self, request, *args, **kwargs):
        """List all words of a unit with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    @matomo_tracking(action_name="Word", resource_id="pk")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single word with Matomo tracking."""
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the queryset of unit word relations

        :return: The queryset of unit word relations
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return UnitWordRelation.objects.none()

        units = Unit.objects.filter(
            resource_id=self.kwargs["unit_id"], released=True, jobs__released=True
        ).distinct()
        if len(units) != 1:
            raise PermissionDenied()
        unit = units[0]

        queryset = (
            UnitWordRelation.objects.select_related("word")
            .filter(
                unit=unit,
                word__audio_check_status="CONFIRMED",
            )
            .filter(
                Q(image_check_status="CONFIRMED")
                | Q(image="", word__image_check_status="CONFIRMED")
            )
            .order_by("word__word")
        )
        return queryset
