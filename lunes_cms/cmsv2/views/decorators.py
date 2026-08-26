from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, JsonResponse

JsonView = Callable[..., JsonResponse]


def require_word_change_permission(view: JsonView) -> JsonView:
    """
    Only let users through who may change words.

    The denial is a JSON response instead of Django's HTML one, because the
    admin JavaScript reads the message of the response and shows it to the user.
    """

    @wraps(view)
    def wrapped_view(request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        if not request.user.has_perm("cmsv2.change_word"):
            return JsonResponse(
                {"status": "error", "message": "Permission denied"}, status=403
            )
        return view(request, *args, **kwargs)

    return wrapped_view
