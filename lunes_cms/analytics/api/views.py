from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

from lunes_cms.analytics.influx import _escape_tag, push_lines
from lunes_cms.cmsv2.models import Job

from ..models import AnalyticsEvent
from .serializers import AnalyticsEventSerializer


class InstallationRateThrottle(SimpleRateThrottle):
    """
    Throttle for installation rates to ensure that users don't send unlimited requests
    """

    scope = "installation"

    def get_cache_key(self, request: Request, _) -> str | None:
        """
        Get the cache key for this request if exists
        """
        installation_id = request.data.get("installation_id")
        if not installation_id:
            return None
        return f"rl:installation:{installation_id}"


class AnalyticsEventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    View class for analytics events
    """

    throttle_classes = [InstallationRateThrottle]
    serializer_class = AnalyticsEventSerializer

    def perform_create(self, serializer: AnalyticsEventSerializer) -> None:
        event = serializer.save()
        if event.event_type == AnalyticsEvent.EventType.EXERCISE_REPETITION:
            payload = event.payload
            exercise_key = payload["exercise_key"]
            exercise_type = exercise_key["exercise_type"]
            session_id = payload["session_id"]
            job_id = exercise_key.get("job_id")
            unit_id = exercise_key.get("unit_id")
            ts = int(event.timestamp.timestamp() * 1_000_000_000)

            if job_id is not None:
                job_name = (
                    Job.objects.filter(id=job_id).values_list("name", flat=True).first()
                )
                key_tag = f"job={_escape_tag(job_name or f'unknown_{job_id}')}"
            else:
                key_tag = f"unit_id={unit_id}"

            push_lines(
                [
                    f"lunes_exercise_repetition"
                    f",{key_tag}"
                    f",exercise_type={exercise_type}"
                    f",session_id={session_id}"
                    f" repetition_count=1i {ts}"
                ]
            )


class AnalyticsGDPRViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """View class for viewing and deleting personal data"""

    serializer_class = AnalyticsEventSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "gdpr"

    def get_queryset(self) -> QuerySet[AnalyticsEvent]:
        return AnalyticsEvent.objects.filter(
            installation_id=self.kwargs["installation_id"]
        )

    def destroy(self, _, *_args, **_kwargs) -> Response:
        """
        Deletes all events with a matching installation_id
        """
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
