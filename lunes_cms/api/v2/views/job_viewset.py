from django.db.models import Count, Q
from rest_framework import viewsets

from ..matomo_tracking import matomo_tracking
from ..serializers import JobSerializer
from ....cmsv2.models import Job


class JobViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all jobs, or a single job by id
    """

    serializer_class = JobSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All jobs")
    def list(self, request, *args, **kwargs):
        """List all jobs with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get the queryset of jobs

        :return: The queryset of jobs
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Job.objects.none()

        queryset = Job.objects.filter(
            released=True,
        ).annotate(number_units=Count("units", filter=Q(units__released=True)))
        return queryset.order_by("name")
