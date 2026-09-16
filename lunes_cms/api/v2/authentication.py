"""
Authentication of the clients of an area.

A client that redeemed a code sends the access token it received with every
request. A client of the main app sends nothing and keeps working exactly as it
did before areas existed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from ...cmsv2.models import AreaAccessToken
from ..utils import get_key

if TYPE_CHECKING:
    from typing import Any

    from rest_framework.request import Request

    from ...cmsv2.models import Area

#: The keyword the token is sent with in the ``Authorization`` header, see
#: :func:`~lunes_cms.api.utils.get_key`. It is the same keyword the v1 API uses
#: for its group API keys, so that a client needs one way of sending a
#: credential rather than one per API version.
AREA_TOKEN_KEYWORD = "Api-Key"


class AreaTokenAuthentication(BaseAuthentication):
    """
    Resolve the area access token of a request, if it sent one.

    This is authentication in the sense of the REST framework only: the token
    identifies an area, not a user, and it grants no permission that an
    anonymous client does not have. All it does is decide which content the
    read-only endpoints answer with.
    """

    keyword = AREA_TOKEN_KEYWORD

    def authenticate(
        self, request: "Request"
    ) -> tuple[AnonymousUser, AreaAccessToken] | None:
        """
        Resolve the token of the request.

        :param request: The request to authenticate
        :return: The anonymous user and the resolved token, or ``None`` if the
                 request carries no token at all
        :raises ~rest_framework.exceptions.AuthenticationFailed: If a token was
                sent that cannot be resolved
        """
        token = get_key(request, keyword=self.keyword)
        if token is None:
            return None
        access_token = AreaAccessToken.resolve(token)
        if access_token is None:
            raise AuthenticationFailed(
                {
                    "detail": _("This access token is not valid."),
                    "error": "invalid_area_token",
                }
            )
        access_token.touch()
        return AnonymousUser(), access_token

    def authenticate_header(self, request: "Request") -> str:
        """
        Make the REST framework answer with 401 instead of 403.

        :param request: The request that was rejected
        :return: The value of the ``WWW-Authenticate`` header
        """
        return self.keyword


def request_area(request: "Request") -> "Area | None":
    """
    The area a request is made for.

    :param request: The request in question
    :return: The area of the access token, or ``None`` for the main app
    """
    return getattr(request.auth, "area", None)


class AreaTokenScheme(OpenApiAuthenticationExtension):
    """
    Document the area access token in the schema.

    This lives next to the authentication class and not with the other schema
    code, because drf-spectacular only knows the extensions that were imported
    before a schema is generated, and the postprocessing hooks are imported
    after the security schemes have been built.
    """

    target_class = AreaTokenAuthentication
    name = "areaToken"

    def get_security_definition(self, auto_schema: "Any") -> dict[str, "Any"]:
        """
        The security scheme of the area access token.

        :param auto_schema: The schema the definition is added to
        :return: The OpenAPI security scheme
        """
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": (
                f"The access token of an area, sent as `{AREA_TOKEN_KEYWORD} "
                "<token>`. A request without it is answered with the content "
                "of the main app, a request with it with the content of the "
                "area the token was issued for. Tokens are handed out by "
                "`/api/v2/areas/register/`."
            ),
        }
