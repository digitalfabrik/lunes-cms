"""
URL patterns for the public Bildschatz website.
"""

from django.urls import path

from . import views

#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "bildschatz"

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", views.index, name="index"),
]
