from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_words
from ..models import Word
from .decorators import require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def update_word_audio_check_status(request: HttpRequest, word_id: int) -> JsonResponse:
    """
    Update the audio check status for a word.

    Args:
        request: The HTTP request
        word_id: The ID of the word to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        word = visible_words(request.user).get(id=word_id)
    except Word.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": _("Word not found")}, status=404
        )

    audio_check_status = request.POST.get("audio_check_status")
    if not audio_check_status:
        return JsonResponse(
            {"status": "error", "message": _("No audio check status provided")},
            status=400,
        )

    word.audio_check_status = audio_check_status
    word.save()

    return JsonResponse(
        {"status": "success", "message": _("Audio check status updated successfully")}
    )
