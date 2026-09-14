"""
Views that serve the well-known files required for iOS Universal Links and
Android App Links, so links like ``https://content.lunes.app/activation/<code>``
open directly in the Lunes app instead of the browser.
"""

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def apple_app_site_association(
    request: HttpRequest,  # pylint: disable=unused-argument
) -> JsonResponse:
    """
    Serve the ``apple-app-site-association`` file at
    ``/.well-known/apple-app-site-association``, required for iOS
    Universal Links.

    :param request: The current HTTP request
    :return: The association file as JSON
    """
    app_id = f"{settings.IOS_APP_TEAM_ID}.{settings.IOS_APP_BUNDLE_ID}"
    prefix = settings.APP_LINK_PATH_PREFIX
    data = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": app_id,
                    "components": [
                        {
                            "/": f"{prefix}/*",
                            "comment": f"Matches any URL with a path that starts with {prefix}/.",
                        },
                    ],
                }
            ],
        }
    }
    return JsonResponse(data, content_type="application/json")


@require_GET
def android_asset_links(
    request: HttpRequest,  # pylint: disable=unused-argument
) -> JsonResponse:
    """
    Serve the ``assetlinks.json`` file at ``/.well-known/assetlinks.json``,
    required for Android App Links.

    :param request: The current HTTP request
    :return: The asset links file as JSON
    """
    data = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": settings.ANDROID_APP_PACKAGE_NAME,
                "sha256_cert_fingerprints": settings.ANDROID_APP_SHA256_CERT_FINGERPRINTS,
            },
        }
    ]
    return JsonResponse(data, content_type="application/json", safe=False)
