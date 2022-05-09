"""
Lunes CMS URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
https://docs.djangoproject.com/en/2.2/topics/http/urls/

Examples:

Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

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


#: The url patterns of this module (see :doc:`topics/http/urls`)
urlpatterns = [
    path("", RedirectView.as_view(url=reverse_lazy("admin:login"))),
    path(
        "favicon.ico",
        RedirectView.as_view(url=get_static_url("images/logo.svg")),
    ),
    path("", include("lunes_cms.cms.urls")),
    url(r"^i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
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
    url(r"^admin/", admin.site.urls),
    path("i18n.js", JavaScriptCatalog.as_view(), name="javascript-translations"),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Set dashboard title
admin.site.index_title = _("Dashboard")
