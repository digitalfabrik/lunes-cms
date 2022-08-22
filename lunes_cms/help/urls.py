"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""
from django.urls import path

from . import views


#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("public_upload", views.public_upload, name="public_upload"),
]
