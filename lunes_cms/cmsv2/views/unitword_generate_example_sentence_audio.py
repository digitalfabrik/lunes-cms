import os
import uuid

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.utils import get_openai_client, OpenAIConfigurationError
from lunes_cms.core import settings


@staff_member_required
def unitword_generate_example_sentence_audio(request, unitword_id):
    """
    Dedicated view for generating audio for a unit-word relation's example sentence.
    """

    unitword_instance = get_object_or_404(UnitWordRelation, pk=unitword_id)

    context = admin.site.each_context(request)
    context.update(
        {
            "unitword_instance": unitword_instance,
            "example_sentence_text": unitword_instance.example_sentence,
            "temp_audio_url": None,
            "temp_audio_filename": None,
        }
    )

    return render(
        request, "admin/unitword_generate_example_sentence_audio.html", context
    )


@staff_member_required
@csrf_exempt
@require_POST
def unitword_generate_example_sentence_audio_via_openai(request):
    """
    AJAX endpoint to generate example sentence audio using OpenAI and save it temporarily.
    Returns the URL/path to the temporary file.
    """

    example_sentence_text = request.POST.get("example_sentence_text")
    if not example_sentence_text:
        return JsonResponse({"error": "No example_sentence_text provided."}, status=400)

    os.makedirs(settings.TEMP_AUDIO_DIR, exist_ok=True)

    try:
        client = get_openai_client()

        response = client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input=example_sentence_text,
        )

        temp_filename = f"temp_audio_{uuid.uuid4().hex}.mp3"
        temp_filepath = os.path.join(settings.TEMP_AUDIO_DIR, temp_filename)

        with open(temp_filepath, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=4096):
                f.write(chunk)

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
    except (ValueError, ConnectionError, TimeoutError) as e:
        return JsonResponse({"error": str(e)}, status=500)


@staff_member_required
@csrf_exempt
@require_POST
def unitword_store_generated_example_sentence_audio_permanently(request, unitword_id):
    """
    Moves the temporary audio file to the UnitWordRelation instance's example_sentence_audio field
    and redirects back to the appropriate admin view.
    """

    unitword_instance = get_object_or_404(UnitWordRelation, pk=unitword_id)
    temp_filename = request.POST.get("temp_audio_filename")

    # Determine redirect URL based on referer
    referer = request.META.get("HTTP_REFERER", "")
    if "word" in referer and unitword_instance.word:
        redirect_url = f"/admin/cmsv2/word/{unitword_instance.word.pk}/change/"
    else:
        redirect_url = f"/admin/cmsv2/unit/{unitword_instance.unit.pk}/change/"

    if not temp_filename:
        return redirect(redirect_url)

    temp_filepath = os.path.join(settings.TEMP_AUDIO_DIR, temp_filename)

    if not os.path.exists(temp_filepath):
        return redirect(redirect_url)

    try:
        with open(temp_filepath, "rb") as f:
            word_text = unitword_instance.word.word.replace(" ", "_")
            unit_text = unitword_instance.unit.title.replace(" ", "_")
            content_file = ContentFile(
                f.read(), name=f"{word_text}_{unit_text}_example_sentence.mp3"
            )
            unitword_instance.example_sentence_audio.save(
                content_file.name, content_file
            )
        unitword_instance.save()

        os.remove(temp_filepath)

        return redirect(redirect_url)

    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error storing generated example sentence audio: {e}")
        return redirect(redirect_url)
