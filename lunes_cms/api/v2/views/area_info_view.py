from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from ....cmsv2.models import AreaCode
from ..serializers import AreaCodeSerializer, AreaInfoResponseSerializer
from .area_registration_view import InvalidAreaCode


@extend_schema(
    summary="Look up the area of a code",
    description=(
        "Look up the area a code belongs to, without redeeming it: no access "
        "token is issued and no client is registered.\n\n"
        "Useful to show the branding of an area, e.g. before a user commits "
        "to actually redeeming its code via `/api/v2/areas/register/`."
    ),
    request=AreaCodeSerializer,
    responses={
        status.HTTP_200_OK: AreaInfoResponseSerializer,
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
class AreaInfoView(APIView):
    """
    Look up the area a code belongs to, without redeeming it.

    Unlike :class:`~lunes_cms.api.v2.views.area_registration_view.AreaRegistrationView`,
    this issues no access token and registers no client. It only tells a
    caller which area a code belongs to.
    """

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "area_info"
    serializer_class = AreaCodeSerializer

    def post(self, request: Request, *_args: Any, **_kwargs: Any) -> Response:
        """
        Look up the area of a code.

        :param request: The request with the code to look up
        :return: The area the code belongs to
        :raises InvalidAreaCode: If no area has the given code
        """
        serializer = AreaCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = (
            AreaCode.objects.select_related("area")
            .filter(code=serializer.validated_data["code"])
            .first()
        )
        if code is None:
            raise InvalidAreaCode()

        return Response(
            AreaInfoResponseSerializer(
                {"area": code.area},
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )
