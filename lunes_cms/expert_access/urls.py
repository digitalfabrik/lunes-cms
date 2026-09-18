"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""

from django.conf import settings
from django.contrib.auth.views import (
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
)
from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from . import views

#: The namespace for this URL config (see :attr:`django.urls.ResolverMatch.app_name`)
app_name = "expert_access"

#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path(
        "", RedirectView.as_view(url=reverse_lazy("expert_access:review")), name="index"
    ),
    path("review/", views.review, name="review"),
    path(
        "logout/",
        LogoutView.as_view(next_page=settings.LOGIN_URL),
        name="logout",
    ),
    path(
        "password/",
        PasswordChangeView.as_view(
            template_name="password_change.html",
            success_url=reverse_lazy("expert_access:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password/done/",
        PasswordChangeDoneView.as_view(template_name="password_change_done.html"),
        name="password_change_done",
    ),
]
