"""
URL patterns for the second version of the Lunes API
"""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from ..utils import OptionalSlashRouter
from . import views

#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "v2"

#: Router for dynamic url patterns
router = OptionalSlashRouter()
router.register(r"feedback", views.CreateFeedbackViewSet, basename="feedback")
router.register(r"jobs", views.JobViewSet, "jobs")
router.register(r"jobs/(?P<job_id>[0-9]+)/units", views.JobUnitsViewSet, "units-of-job")
router.register(r"jobs/(?P<job_id>[0-9]+)/words", views.JobWordsViewSet, "words-of-job")
router.register(r"sponsors", views.SponsorsViewSet, "sponsors")
router.register(
    r"units/(?P<unit_id>[0-9]+)/words", views.UnitWordViewSet, "words-of-units"
)
router.register(r"words", views.WordViewSet, "words")

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            template_name="swagger_ui.html", url_name="api:v2:schema"
        ),
        name="swagger-ui",
    ),
]
