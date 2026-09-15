from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from ....cmsv2.models import AreaAccessToken, AreaCode
from ..serializers import AreaRegistrationResponseSerializer, AreaRegistrationSerializer


class InvalidAreaCode(APIException):
    """
    Exception for a code that no area has.

    This is answered with ``400`` and not with ``404``, so that a wrong code
    cannot be told apart from a wrong URL by an automated prober, and so that a
    client can tell a code its user mistyped from a broken build of its own.

    The identifier is called ``error`` and not ``code``: the request field is
    called ``code``, so a missing one produces the field error ``{"code":
    ["This field is required."]}`` and a client checking ``body["code"]`` would
    find a string here and a list there.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = {
        "detail": _("This code is not valid."),
        "error": "invalid_area_code",
    }


@extend_schema(
    summary="Redeem the code of an area",
    description=(
        "Redeem the code of an area and register this client instance.\n\n"
        "The client receives an access token that does not expire. Sending "
        "that token in the `Authorization` header as `Api-Key <token>` "
        "makes every other endpoint answer with the content of the area "
        "instead of the content of the main app.\n\n"
        "The token is only sent in this answer, because the server stores "
        "nothing but its hash. A client that lost its token redeems its code "
        "again."
    ),
    request=AreaRegistrationSerializer,
    responses={
        status.HTTP_201_CREATED: AreaRegistrationResponseSerializer,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="The code is unknown or the request is incomplete.",
            examples=[
                OpenApiExample(
                    "Unknown code",
                    value={
                        "detail": "This code is not valid.",
                        "error": "invalid_area_code",
                    },
                ),
            ],
        ),
    },
    auth=[],
)
class AreaRegistrationView(APIView):
    """
    Redeem the code of an area and register this client instance.

    The client receives an access token that does not expire. Sending that
    token in the ``Authorization`` header as ``Api-Key <token>`` makes every
    other endpoint answer with the content of the area instead of the content
    of the main app.

    The token is only sent in this answer, because the server stores nothing
    but its hash. A client that lost its token redeems its code again.
    """

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "area_registration"
    serializer_class = AreaRegistrationSerializer

    def post(self, request: Request, *_args: Any, **_kwargs: Any) -> Response:
        """
        Redeem a code and issue an access token for its area.

        :param request: The request with the code of the client
        :return: The access token and the area it grants access to
        :raises InvalidAreaCode: If no area has the given code
        """
        serializer = AreaRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = (
            AreaCode.objects.select_related("area")
            .filter(code=serializer.validated_data["code"])
            .first()
        )
        if code is None:
            raise InvalidAreaCode()

        _access_token, token = AreaAccessToken.issue(
            code,
            installation_id=serializer.validated_data.get("installation_id", ""),
        )
        return Response(
            AreaRegistrationResponseSerializer(
                {"token": token, "area": code.area}
            ).data,
            status=status.HTTP_201_CREATED,
        )
