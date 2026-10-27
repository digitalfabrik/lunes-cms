from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.areas import visible_unit_word_relations, visible_words
from lunes_cms.cmsv2.models import UnitWordRelation, Word
from lunes_cms.cmsv2.services.image_generation import (
    build_word_image_prompt,
    GENERATED_IMAGE_EXTENSION,
    openai_image_bytes,
)
from lunes_cms.cmsv2.utils import OpenAIConfigurationError
from lunes_cms.core import settings

from .decorators import json_not_found, require_any_permission_json

if TYPE_CHECKING:
    from lunes_cms.cmsv2.models import Unit

logger = logging.getLogger(__name__)


def _prompt_from_request(
    request: HttpRequest, word: Word, unit: Unit | None = None
) -> str:
    """
    Builds the image prompt for ``word``.

    The prompt context (unit, job) is resolved from the database by
    ``build_word_image_prompt``; the request only contributes the editor's own
    hints.
    """
    return build_word_image_prompt(
        word,
        unit=unit,
        additional_info=request.POST.get("additional_info"),
        allow_text_in_image=request.POST.get("allow_text_in_image") == "true",
    )


def _generate_temp_image(
    request: HttpRequest, word: Word, unit: Unit | None = None
) -> JsonResponse:
    """
    Generates an image for ``word`` and saves it temporarily.

    The generation is recorded for the word's area.
    """
    prompt = _prompt_from_request(request, word, unit)

    try:
        image_data = openai_image_bytes(prompt, word.area)

        os.makedirs(settings.TEMP_IMAGE_DIR, exist_ok=True)

        # The extension has to match the bytes all the way to the ImageField:
        # a WebP stored as .png would be re-encoded on save and lose OpenAI's
        # provenance markings.
        temp_filename = f"temp_image_{uuid.uuid4().hex}{GENERATED_IMAGE_EXTENSION}"
        temp_filepath = os.path.join(settings.TEMP_IMAGE_DIR, temp_filename)

        with open(temp_filepath, "wb") as f:
            f.write(image_data)

        temp_image_url = os.path.join(settings.MEDIA_URL, "temp_image", temp_filename)

        return JsonResponse(
            {
                "message": _("Image generated!"),
                "temp_image_url": temp_image_url,
                "temp_image_filename": temp_filename,
            }
        )

    except OpenAIConfigurationError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except (ValueError, ConnectionError, TimeoutError) as e:
        logger.error("Generating an image failed: %s", e)
        return JsonResponse({"error": str(e)}, status=500)


def _word_or_none(request: HttpRequest, word_id: int) -> Word | None:
    try:
        return visible_words(request.user).get(pk=word_id)
    except Word.DoesNotExist:
        return None


def _unitword_or_none(
    request: HttpRequest, unitword_id: int
) -> UnitWordRelation | None:
    try:
        return (
            visible_unit_word_relations(request.user)
            .select_related("word__area", "unit")
            .get(pk=unitword_id)
        )
    except UnitWordRelation.DoesNotExist:
        return None


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def word_generate_image_via_openai(request: HttpRequest, word_id: int) -> JsonResponse:
    """
    AJAX endpoint to generate an image for a word using OpenAI and save it
    temporarily. Returns the URL/path to the temporary file.
    """
    word = _word_or_none(request, word_id)
    if word is None:
        return json_not_found(_("Word not found"))
    return _generate_temp_image(request, word)


@login_required
@require_any_permission_json("cmsv2.change_word")
@require_POST
def word_image_prompt_preview(request: HttpRequest, word_id: int) -> JsonResponse:
    """
    AJAX endpoint returning the prompt an image generation for the word would
    send, so editors can see it before generating.
    """
    word = _word_or_none(request, word_id)
    if word is None:
        return json_not_found(_("Word not found"))
    return JsonResponse({"prompt": _prompt_from_request(request, word)})


@login_required
@require_any_permission_json("cmsv2.change_unitwordrelation")
@require_POST
def unitword_generate_image_via_openai(
    request: HttpRequest, unitword_id: int
) -> JsonResponse:
    """
    AJAX endpoint to generate an image for a unit<>word relation using OpenAI
    and save it temporarily. Returns the URL/path to the temporary file.
    """
    unitword = _unitword_or_none(request, unitword_id)
    if unitword is None:
        return json_not_found(_("Unit-Word relation not found"))
    return _generate_temp_image(request, unitword.word, unit=unitword.unit)


@login_required
@require_any_permission_json("cmsv2.change_unitwordrelation")
@require_POST
def unitword_image_prompt_preview(
    request: HttpRequest, unitword_id: int
) -> JsonResponse:
    """
    AJAX endpoint returning the prompt an image generation for the unit<>word
    relation would send, so editors can see it before generating.
    """
    unitword = _unitword_or_none(request, unitword_id)
    if unitword is None:
        return json_not_found(_("Unit-Word relation not found"))
    return JsonResponse(
        {"prompt": _prompt_from_request(request, unitword.word, unitword.unit)}
    )
