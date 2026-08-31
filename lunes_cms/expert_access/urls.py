"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""

from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from . import views

#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "expert_access"

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy("expert_access:review")), name="index"),
    path("review/", views.review, name="review"),
]
