"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""
from django.urls import include, path
from django.conf.urls import url
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from ..utils import OptionalSlashRouter
from . import views


#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "v1"

#: Schema view for swagger documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
#: Router for dynamic url patterns
router = OptionalSlashRouter()
router.register(r"disciplines", views.DisciplineViewSet, "disciplines")
router.register(
    r"disciplines_by_level(?:/(?P<discipline_id>[0-9]+))?",
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

#: The url patterns of this module (see :doc:`topics/http/urls`)
urlpatterns = [
    path("", include(router.urls)),
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]
