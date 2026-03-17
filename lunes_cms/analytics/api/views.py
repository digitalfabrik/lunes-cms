from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

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
