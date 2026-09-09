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

from typing import Any

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.templatetags.static import static as get_static_url
from django.urls import include, path, re_path, reverse
from django.views.generic.base import RedirectView

from ..cmsv2.models.static import is_expert


class MainRedirectView(RedirectView):
    """
    Sends users to the entry point matching their role: experts to their review
    view, everyone else to the admin (which handles the login redirect itself).
    """

    permanent = False

    def get_redirect_url(self, *args: Any, **kwargs: Any) -> str:
        """
        :param args: positional arguments captured from the URL
        :param kwargs: keyword arguments captured from the URL

        :return: the URL to redirect the current user to
        """
        if self.request.user.is_authenticated and is_expert(self.request.user):
            return reverse("expert_access:index")
        return reverse("admin:index")


#: The url patterns of this module (see :doc:`django:topics/http/urls`)
urlpatterns = [
    path("", MainRedirectView.as_view()),
    path(
        "favicon.ico",
        RedirectView.as_view(url=get_static_url("images/logo.svg")),
    ),
    path("api/", include("lunes_cms.api.urls", namespace="api")),
    path("", include("lunes_cms.help.urls")),
    re_path(r"^i18n/", include("django.conf.urls.i18n")),
    path("qr_code/", include("qr_code.urls", namespace="qr_code")),
    path("expert/", include("lunes_cms.expert_access.urls", namespace="expert_access")),
]

urlpatterns += i18n_patterns(
    path("admin/cmsv2/", include("lunes_cms.cmsv2.urls", namespace="cmsv2"))
)
urlpatterns += i18n_patterns(path("", include("lunes_cms.cms.urls")))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if getattr(settings, "DEBUG_TOOLBAR_ENABLED", False):
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
