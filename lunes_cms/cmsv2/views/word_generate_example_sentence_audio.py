from __future__ import annotations

import os
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.services.audio_generation import openai_sentence_audio_bytes
from lunes_cms.cmsv2.utils import cache_busted_url, is_ajax, OpenAIConfigurationError
from lunes_cms.core import settings


@staff_member_required
@csrf_exempt
@require_POST
def word_generate_example_sentence_audio_via_openai(
    request: HttpRequest,
) -> JsonResponse:
    """
    AJAX endpoint to generate example sentence audio using OpenAI and save it temporarily.
    Returns the URL/path to the temporary file.
    """

    example_sentence_text = request.POST.get("example_sentence_text")
    if not example_sentence_text:
        return JsonResponse({"error": "No example_sentence_text provided."}, status=400)

    os.makedirs(settings.TEMP_AUDIO_DIR, exist_ok=True)

    try:
        audio_bytes = openai_sentence_audio_bytes(example_sentence_text)

        temp_filename = f"temp_audio_{uuid.uuid4().hex}.mp3"
        temp_filepath = os.path.join(settings.TEMP_AUDIO_DIR, temp_filename)

        with open(temp_filepath, "wb") as f:
            f.write(audio_bytes)

        temp_audio_url = os.path.join(settings.MEDIA_URL, "temp_audio", temp_filename)

        return JsonResponse(
            {
                "message": "Audio generated and saved temporarily!",
                "temp_audio_url": temp_audio_url,
                "temp_audio_filename": temp_filename,
            }
        )

    except OpenAIConfigurationError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except ValidationError as e:
        return JsonResponse({"error": "; ".join(e.messages)}, status=500)
    except (ValueError, ConnectionError, TimeoutError) as e:
        return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_POST
def word_store_generated_example_sentence_audio_permanently(
    request: HttpRequest, word_id: int
) -> HttpResponse:
    """
    Moves the temporary audio file to the Word instance's example_sentence_audio field.

    For AJAX requests (inline regeneration on the change page) it returns a
    JSON response; otherwise it redirects back to the edit view.
    """

    word_instance = get_object_or_404(Word, pk=word_id)
    temp_filename = request.POST.get("temp_audio_filename")

    def failure(message: str, status: int = 400) -> HttpResponse:
        if is_ajax(request):
            return JsonResponse({"status": "error", "message": message}, status=status)
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    if not temp_filename:
        return failure("No temporary audio file provided.")

    temp_filepath = os.path.join(settings.TEMP_AUDIO_DIR, temp_filename)

    if not os.path.exists(temp_filepath):
        return failure("Temporary audio file no longer exists.")

    try:
        with open(temp_filepath, "rb") as f:
            content_file = ContentFile(
                f.read(),
                name=f'{word_instance.word.replace(" ", "_")}_example_sentence.mp3',
            )
            # content_file.name is always the literal set above; ContentFile.name
            # is typed Optional[str] only because the base File class allows it.
            assert content_file.name is not None
            word_instance.example_sentence_audio.save(content_file.name, content_file)
        word_instance.example_sentence_audio_regenerated = True
        word_instance.save()

        os.remove(temp_filepath)

        if is_ajax(request):
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Audio saved successfully.",
                    "audio_url": cache_busted_url(word_instance.example_sentence_audio),
                }
            )
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    except (ValueError, FileNotFoundError, OSError) as e:
        return failure(
            f"Error storing generated example sentence audio: {e}", status=500
        )
