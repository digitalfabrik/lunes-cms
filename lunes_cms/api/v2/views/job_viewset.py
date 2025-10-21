from django.db.models import Count, Q
from rest_framework import viewsets

from ....cmsv2.models import Job
from ..serializers import JobSerializer


class JobViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all jobs, or a single job by id
    """

    serializer_class = JobSerializer
    http_method_names = ["get"]

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
