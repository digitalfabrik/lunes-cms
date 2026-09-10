from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _

ViewFunction = Callable[..., HttpResponse]


def require_any_permission_json(
    *permissions: str,
) -> Callable[[ViewFunction], ViewFunction]:
    """
    Only let users through who hold at least one of the given permissions.

    The denial is a JSON response instead of Django's HTML one, because the
    admin JavaScript reads the message of the response and shows it to the user.
    """

    def decorator(view: ViewFunction) -> ViewFunction:
        @wraps(view)
        def wrapped_view(
            request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            if not any(request.user.has_perm(perm) for perm in permissions):
                return JsonResponse(
                    {"status": "error", "message": _("Permission denied")}, status=403
                )
            return view(request, *args, **kwargs)

        return wrapped_view

    return decorator
