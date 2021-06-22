"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns descriped in the `README.md` file
"""
from django.urls import include, path
from rest_framework import routers
from django.conf.urls import url
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from . import views


# Schema view for swagger documentation
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
# router for dynmaic url patterns
router = routers.DefaultRouter()
#router.register(r"disciplines/$", views.DisciplineViewSet, "disciplines")
router.register(
    r"disciplines(?:/(?P<group_id>[\d+&]+))?", views.DisciplineViewSet, "disciplines", #(?:/(?P<username>[-\w]+))?
)
router.register(
    r"training_set/(?P<discipline_id>[0-9]+)", views.TrainingSetViewSet, "training_set"
)
router.register(
    r"documents/(?P<training_set_id>[0-9]+)", views.DocumentViewSet, "documents"
)


urlpatterns = [
    path("", views.redirect_view, name="redirect"),
    path("public_upload", views.public_upload, name="public_upload"),
    path("api/", include(router.urls)),
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
