from __future__ import annotations

from typing import TYPE_CHECKING

from ..authentication import AreaTokenAuthentication, request_area

if TYPE_CHECKING:
    from ....cmsv2.models import Area


class AreaScopedMixin:
    """
    Mixin for the read-only endpoints that publish content.

    It resolves the access token of the request, if there is one, and offers
    the area it belongs to as :attr:`area`. Every viewset that publishes jobs,
    units or words has to use it, so that a client of an area sees the content
    of its area and a client without a token keeps seeing the main app.
    """

    authentication_classes = [AreaTokenAuthentication]

    @property
    def area(self) -> "Area | None":
        """
        The area this request is made for.

        :return: The area of the access token, the main app area for a
            request without one, or ``None`` during schema generation, when
            there is no real request to resolve at all
        """
        request = getattr(self, "request", None)
        if request is None or getattr(self, "swagger_fake_view", False):
            return None
        return request_area(request)
