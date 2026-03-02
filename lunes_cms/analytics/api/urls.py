from typing import List, Union

from django.urls import URLPattern, URLResolver, include, path

from ...api.utils import OptionalSlashRouter
from .views import AnalyticsEventViewSet

app_name = "analytics"

router = OptionalSlashRouter()
router.register(r"events", AnalyticsEventViewSet, basename="analytics_event")

urlpatterns: List[Union[URLPattern, URLResolver]] = [
    path("", include(router.urls)),
]
