from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_words
from ..models import Word
from ..models.static import CheckStatus
from .decorators import json_not_found, require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def update_word_example_sentence_check_status(
    request: HttpRequest, word_id: int
) -> JsonResponse:
    """
    Update the example sentence check status for a word.

    Args:
        request: The HTTP request
        word_id: The ID of the word to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        word = visible_words(request.user).get(id=word_id)
    except Word.DoesNotExist:
        return json_not_found(_("Word not found"))

    example_sentence_check_status = request.POST.get("example_sentence_check_status")
    if not example_sentence_check_status:
        return JsonResponse(
            {
                "status": "error",
                "message": _("No example sentence check status provided"),
            },
            status=400,
        )
    if example_sentence_check_status not in CheckStatus.values:
        return JsonResponse(
            {
                "status": "error",
                "message": _("Invalid example sentence check status"),
            },
            status=400,
        )

    word.example_sentence_check_status = example_sentence_check_status
    word.save()

    return JsonResponse(
        {
            "status": "success",
            "message": _("Example sentence check status updated successfully"),
        }
    )
