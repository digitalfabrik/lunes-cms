from __future__ import annotations

from typing import Any

from django.db.models import Count, Q, QuerySet
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from ....cmsv2.areas import published_jobs
from ....cmsv2.models import Job
from ..matomo_tracking import matomo_tracking
from ..serializers import JobSerializer
from .area_scoped_mixin import AreaScopedMixin


class JobViewSet(AreaScopedMixin, viewsets.ModelViewSet):
    """
    Retrieve the list of all jobs, or a single job by id

    Without an area access token these are the jobs of the main app, with one
    they are the jobs of that area.
    """

    serializer_class = JobSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All jobs")
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """List all jobs with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Job]:
        """
        Get the queryset of jobs

        :return: The queryset of jobs
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Job.objects.none()

        area = self.area
        assert area is not None
        queryset = published_jobs(
            Job.objects.filter(released=True, archived=False), area
        ).annotate(number_units=Count("units", filter=Q(units__released=True)))
        return queryset.order_by("name")
