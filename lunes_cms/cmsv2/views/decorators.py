from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TYPE_CHECKING

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise

ViewFunction = Callable[..., HttpResponse]


def json_not_found(message: "_StrOrPromise") -> JsonResponse:
    """
    The JSON answer for an object the user may not see.

    The admin JavaScript reads the message of the response and shows it to the
    user, so a missing object is reported in the same shape as a denial.
    """
    return JsonResponse({"status": "error", "message": message}, status=404)


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
