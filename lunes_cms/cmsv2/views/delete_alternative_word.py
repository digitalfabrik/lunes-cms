from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import AlternativeWord
from .decorators import require_word_change_permission


@login_required
@require_word_change_permission
@csrf_exempt
@require_POST
def delete_alternative_word(
    _request: HttpRequest, alternative_word_id: int
) -> JsonResponse:
    """
    Delete an alternative word.

    Args:
        _request: The HTTP request
        alternative_word_id: The ID of the alternative word to delete

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        alternative_word = AlternativeWord.objects.get(id=alternative_word_id)
    except AlternativeWord.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Alternative word not found"}, status=404
        )

    alternative_word.delete()

    return JsonResponse(
        {"status": "success", "message": "Alternative word deleted successfully"}
    )
