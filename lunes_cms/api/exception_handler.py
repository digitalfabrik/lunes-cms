from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(
    exception: Exception, context: dict[str, Any]
) -> Response | None:
    """
    Extend the default exception_handler of rest_framework.
    Purpose: Simplify testing by ensuring that the detail message is the same for all 404 responses.
    """

    response = exception_handler(exception, context)

    if getattr(response, "status_code", None) == status.HTTP_404_NOT_FOUND:
        response.data["detail"] = "Not found."

    return response
