"""
Map paths to view functions.
Defines custom schema views and a router that
handles the url patterns described in the `README.md` file
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls import url
from django.templatetags.static import static as get_static_url
from django.urls import path, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import RedirectView
from django.views.i18n import JavaScriptCatalog


#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path(
        "admin/password_reset/",
        auth_views.PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "admin/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("admin/", admin.site.urls),
    path("i18n.js", JavaScriptCatalog.as_view(), name="javascript-translations"),
]

# Set dashboard title
admin.site.index_title = _("Dashboard")
