from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_alternative_words, visible_words
from ..models import AlternativeWord, Word
from .decorators import require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def save_alternative_word(request: HttpRequest) -> JsonResponse:
    """
    Create or update an alternative word.

    If an ``alternative_word_id`` is provided, the existing alternative word
    is updated, otherwise a new one is created for the word given by ``word_id``.

    Args:
        request: The HTTP request

    Returns:
        JsonResponse: A response indicating success or failure
    """
    if alternative_word_id := request.POST.get("alternative_word_id"):
        try:
            alternative_word = visible_alternative_words(request.user).get(
                id=alternative_word_id
            )
        except (AlternativeWord.DoesNotExist, ValueError):
            return JsonResponse(
                {"status": "error", "message": _("Alternative word not found")},
                status=404,
            )
    else:
        word_id = request.POST.get("word_id")
        if not word_id:
            return JsonResponse(
                {"status": "error", "message": _("No word id provided")}, status=400
            )
        try:
            word = visible_words(request.user).get(id=word_id)
        except (Word.DoesNotExist, ValueError):
            return JsonResponse(
                {"status": "error", "message": _("Word not found")}, status=404
            )
        alternative_word = AlternativeWord(word=word)

    alt_word = (request.POST.get("alt_word") or "").strip()
    if not alt_word:
        return JsonResponse(
            {"status": "error", "message": _("No alternative word provided")},
            status=400,
        )

    alternative_word.alt_word = alt_word
    alternative_word.plural = request.POST.get("plural", "")
    try:
        for field in ("grammatical_gender", "singular_article", "plural_article"):
            raw_value = request.POST.get(field)
            setattr(alternative_word, field, int(raw_value) if raw_value else None)
        alternative_word.full_clean()
    except (ValueError, ValidationError):
        return JsonResponse(
            {"status": "error", "message": _("Invalid field value provided")},
            status=400,
        )

    alternative_word.save()

    return JsonResponse(
        {"status": "success", "message": _("Alternative word saved successfully")}
    )
