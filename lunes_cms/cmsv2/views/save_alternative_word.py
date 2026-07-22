from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import AlternativeWord, Word


@staff_member_required
@csrf_exempt
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
            alternative_word = AlternativeWord.objects.get(id=alternative_word_id)
        except AlternativeWord.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Alternative word not found"}, status=404
            )
    else:
        try:
            word = Word.objects.get(id=request.POST.get("word_id"))
        except (Word.DoesNotExist, ValueError):
            return JsonResponse(
                {"status": "error", "message": "Word not found"}, status=404
            )
        alternative_word = AlternativeWord(word=word)

    alt_word = (request.POST.get("alt_word") or "").strip()
    if not alt_word:
        return JsonResponse(
            {"status": "error", "message": "No alternative word provided"}, status=400
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
            {"status": "error", "message": "Invalid field value provided"}, status=400
        )

    alternative_word.save()

    return JsonResponse(
        {"status": "success", "message": "Alternative word saved successfully"}
    )
