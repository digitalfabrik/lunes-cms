"""
Map paths to view functions.
"""

from django.urls import path

from . import views

urlpatterns = [
    path(
        "activation/<str:code>/",
        views.activation_landing_page,
        name="activation-landing-page",
    ),
]
