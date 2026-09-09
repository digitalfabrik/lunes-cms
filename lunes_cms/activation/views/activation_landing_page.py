from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def activation_landing_page(request: HttpRequest, code: str) -> HttpResponse:
    """
    Public landing page served at ``/activation/<code>``.

    On a phone with the Lunes app installed, this path is intercepted by the
    OS (iOS Universal Links / Android App Links, see
    :func:`~lunes_cms.core.views.apple_app_site_association` and
    :func:`~lunes_cms.core.views.android_asset_links`) and the request never
    reaches the server. Whenever it does reach the server, the app either
    is not installed, or the OS could not route the link to it, so this page
    explains the situation, offers a button that retries opening the app via
    its custom URL scheme, and links to both app stores.

    :param request: The current HTTP request
    :param code: The activation code from the URL, forwarded to the app via
        the custom scheme deeplink
    :return: The rendered landing page
    """
    context = {
        "deeplink_url": f"lunes:lunes.app/activation/{code}",
        "code": code,
        "android_store_url": (
            "https://play.google.com/store/apps/details"
            f"?id={settings.ANDROID_APP_PACKAGE_NAME}"
        ),
        "ios_store_url": "https://apps.apple.com/de/app/lunes/id1562834995",
    }
    return render(request, "activation_landing_page.html", context)
