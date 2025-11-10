from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from ....cmsv2.models import Unit
from ..serializers import UnitWordRelationSerializer
from ....cmsv2.models.unit import UnitWordRelation


class UnitWordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words that belong to a given unit
    """

    serializer_class = UnitWordRelationSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of unit word relations

        :return: The queryset of unit word relations
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return UnitWordRelation.objects.none()

        units = Unit.objects.filter(
            id=self.kwargs["unit_id"], released=True, jobs__released=True
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
            .filter(
                Q(example_sentence="")
                | Q(
                    example_sentence_check_status="CONFIRMED",
                    example_sentence_audio__gt="",
                )
                | Q(
                    word__example_sentence__gt="",
                    word__example_sentence_check_status="CONFIRMED",
                    word__example_sentence_audio__gt="",
                )
            )
            .order_by("word__word")
        )
        return queryset
