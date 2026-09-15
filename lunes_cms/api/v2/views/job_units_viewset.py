from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from ....cmsv2.areas import published_units
from ....cmsv2.models import Job, Unit
from ..matomo_tracking import matomo_tracking
from ..serializers import UnitSerializer
from .area_scoped_mixin import AreaScopedMixin


class JobUnitsViewSet(AreaScopedMixin, viewsets.ModelViewSet):
    """
    Retrieve the list of all units that belong to a job

    The job has to belong to the area of the access token of the request, or to
    the main app if the request carries no token.
    """

    serializer_class = UnitSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All units of job", resource_id="job_id")
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """List all units of a job with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    @matomo_tracking(action_name="Unit", resource_id="pk")
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retrieve a single unit with Matomo tracking."""
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Unit]:
        """
        Get the queryset of all released units of a job

        :return: The queryset of units
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Unit.objects.none()

        try:
            job = Job.objects.get(pk=self.kwargs["job_id"])
        except Job.DoesNotExist as e:
            raise PermissionDenied() from e

        area = self.area
        if not job.released or job.archived or job.area_id != getattr(area, "pk", None):
            raise PermissionDenied()

        units = published_units(
            Unit.objects.filter(jobs__pk=job.pk, released=True), area
        )
        queryset = Unit.objects.filter(pk__in=units).annotate(
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
