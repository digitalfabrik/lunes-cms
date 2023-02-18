"""
URL patterns for the first version of the Lunes API
"""
from django.urls import include, path, re_path

from rest_framework import permissions
from rest_framework.versioning import NamespaceVersioning

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from ..utils import OptionalSlashRouter
from . import views


#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "v1"

#: Router for dynamic url patterns
router = OptionalSlashRouter()
router.register(r"disciplines", views.DisciplineViewSet, "disciplines")
router.register(
    "disciplines_by_level/",
    views.DisciplineFilteredViewSet,
    "disciplines_overview",
)
router.register(
    r"disciplines_by_level/(?P<discipline_id>[0-9]+)?",
    views.DisciplineFilteredViewSet,
    "disciplines_by_level",
)
router.register(
    r"disciplines_by_group/(?P<group_id>[0-9]+)",
    views.DisciplineFilteredViewSet,
    "discipline_by_group",
)
router.register(
    r"training_set/(?P<discipline_id>[0-9]+)", views.TrainingSetViewSet, "training_set"
)
router.register(
    r"training_sets",
    views.TrainingSetByIdViewSet,
    "training_sets",
)
router.register(
    r"documents/(?P<training_set_id>[0-9]+)", views.DocumentViewSet, "documents"
)

router.register(
    r"document_by_id/(?P<document_id>[0-9]+)", views.DocumentByIdViewSet, "documents"
)
router.register(r"words", views.WordViewSet, "words")
router.register(r"group_info", views.GroupViewSet, "group_by_id")
router.register(r"feedback", views.CreateFeedbackViewSet, "feedback")
router.register(r"sponsors", views.SponsorsViewSet, "sponsors")

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            template_name="swagger_ui.html", url_name="api:v1:schema"
        ),
        name="swagger-ui",
    ),
]
