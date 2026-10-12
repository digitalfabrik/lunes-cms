from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_words
from ..models import Word
from ..utils import cache_busted_url
from .decorators import require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def update_word_audio(request: HttpRequest, word_id: int) -> JsonResponse:
    """
    Update the audio file for a word.

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

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "audio" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": _("No audio file provided")}, status=400
            )

        word.audio = request.FILES["audio"]
        word.save()

        return JsonResponse(
            {
                "status": "success",
                "message": _("Audio added successfully"),
                "audio_url": cache_busted_url(word.audio) if word.audio else None,
            }
        )

    if action == "delete":
        if word.audio:
            word.audio.delete()
            word.audio = None
            word.save()

            return JsonResponse(
                {"status": "success", "message": _("Audio deleted successfully")}
            )

        return JsonResponse(
            {"status": "error", "message": _("No audio file to delete")}, status=400
        )

    return JsonResponse({"status": "error", "message": _("Invalid action")}, status=400)
