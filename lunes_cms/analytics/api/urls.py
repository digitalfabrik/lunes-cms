from typing import List, Union

from django.urls import include, path, URLPattern, URLResolver

from ...api.utils import OptionalSlashRouter
from .views import AnalyticsEventViewSet, AnalyticsGDPRViewSet

app_name = "analytics"

router = OptionalSlashRouter()
router.register(r"events", AnalyticsEventViewSet, basename="analytics_event")

urlpatterns: List[Union[URLPattern, URLResolver]] = [
    path("", include(router.urls)),
    path(
        "export/<slug:installation_id>/",
        AnalyticsGDPRViewSet.as_view({"get": "list"}),
        name="analytics_gdpr_export",
    ),
    path(
        "data/<slug:installation_id>/",
        AnalyticsGDPRViewSet.as_view({"delete": "destroy"}),
        name="analytics_gdpr_data",
    ),
]
