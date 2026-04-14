from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

from ..matomo_event_tracking import forward_analytics_event_to_matomo
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

    def perform_create(self, serializer):
        serializer.save()
        forward_analytics_event_to_matomo(
            event_type=serializer.validated_data["event_type"],
            payload=serializer.validated_data["payload"],
            request=self.request,
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

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Deletes all events with a matching installation_id
        """
        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
