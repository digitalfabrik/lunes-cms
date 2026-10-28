from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_words
from ..models import Word
from ..utils import cache_busted_url, is_not_blank
from .decorators import json_not_found, require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def update_word_example_sentence_audio(
    request: HttpRequest, word_id: int
) -> JsonResponse:
    """
    Upload or delete the audio file of a word's example sentence.

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

    action = request.POST.get("action")

    if action in ("add", "replace"):
        error = None
        if not is_not_blank(word.example_sentence):
            error = _("The word has no example sentence")
        elif "audio" not in request.FILES:
            error = _("No audio file provided")
        if error:
            return JsonResponse({"status": "error", "message": error}, status=400)

        word.example_sentence_audio = request.FILES["audio"]
        word.save()

        return JsonResponse(
            {
                "status": "success",
                "message": _("Audio added successfully"),
                "audio_url": cache_busted_url(word.example_sentence_audio),
            }
        )

    if action == "delete":
        if word.example_sentence_audio:
            word.example_sentence_audio.delete()
            word.example_sentence_audio = None
            word.save()

            return JsonResponse(
                {"status": "success", "message": _("Audio deleted successfully")}
            )

        return JsonResponse(
            {"status": "error", "message": _("No audio file to delete")}, status=400
        )

    return JsonResponse({"status": "error", "message": _("Invalid action")}, status=400)
