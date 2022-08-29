"""
URL patterns for the Lunes API
"""
from django.urls import include, path


#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "api"

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", include("lunes_cms.api.v1.urls", namespace="default")),
    path("v1/", include("lunes_cms.api.v1.urls", namespace="v1")),
]
