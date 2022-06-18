"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""
from django.urls import include, path


#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "api"

#: The url patterns of this module (see :doc:`topics/http/urls`)
urlpatterns = [
    path("", include("lunes_cms.api.v1.urls", namespace="default")),
    path("v1/", include("lunes_cms.api.v1.urls", namespace="v1")),
]
