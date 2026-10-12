from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_alternative_words
from ..models import AlternativeWord
from .decorators import require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def delete_alternative_word(
    request: HttpRequest, alternative_word_id: int
) -> JsonResponse:
    """
    Delete an alternative word.

    Args:
        request: The HTTP request
        alternative_word_id: The ID of the alternative word to delete

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        alternative_word = visible_alternative_words(request.user).get(
            id=alternative_word_id
        )
    except AlternativeWord.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": _("Alternative word not found")}, status=404
        )

    alternative_word.delete()

    return JsonResponse(
        {"status": "success", "message": _("Alternative word deleted successfully")}
    )
