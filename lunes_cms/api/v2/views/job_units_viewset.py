from django.db.models import Q, Count
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from ..serializers import UnitSerializer
from ....cmsv2.models import Unit, Job


class JobUnitsViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all units that belong to a job
    """

    serializer_class = UnitSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of all released units of a job

        :return: The queryset of units
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Unit.objects.none()

        try:
            job = Job.objects.get(id=self.kwargs["job_id"])
        except Job.DoesNotExist as e:
            raise PermissionDenied() from e

        if not job.released:
            raise PermissionDenied()

        queryset = Unit.objects.filter(jobs__id=job.id, released=True).annotate(
            number_words=Count(
                "unit_word_relations",
                filter=Q(
                    unit_word_relations__word__audio_check_status="CONFIRMED",
                )
                & (
                    Q(
                        unit_word_relations__image="",
                        unit_word_relations__word__image_check_status="CONFIRMED",
                    )
                    | Q(unit_word_relations__image_check_status="CONFIRMED")
                ),
            )
        )
        return queryset.order_by("title")
