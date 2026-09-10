from __future__ import annotations

import os
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.services.image_generation import (
    build_image_prompt,
    generated_image_extension,
    openai_image_bytes,
)
from lunes_cms.cmsv2.utils import OpenAIConfigurationError
from lunes_cms.core import settings


def _prompt_from_request(request: HttpRequest) -> str | None:
    """
    Builds the image-generation prompt from POST data, or None if the
    required word text is missing.
    """
    word_text = request.POST.get("word_text")
    if not word_text:
        return None
    return build_image_prompt(
        word_text,
        request.POST.get("unit_title"),
        request.POST.get("additional_info"),
        job_title=request.POST.get("job_title"),
        allow_text_in_image=request.POST.get("allow_text_in_image") == "true",
    )


@staff_member_required
@csrf_exempt
@require_POST
def generate_image_via_openai(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to generate image using OpenAI and save it temporarily.
    Returns the URL/path to the temporary file.
    """

    prompt = _prompt_from_request(request)
    if prompt is None:
        return JsonResponse({"error": "No word_text provided."}, status=400)

    try:
        image_data = openai_image_bytes(prompt)

        os.makedirs(settings.TEMP_IMAGE_DIR, exist_ok=True)

        # The extension has to match the bytes all the way to the ImageField:
        # a WebP stored as .png would be re-encoded on save and lose OpenAI's
        # provenance markings.
        temp_filename = f"temp_image_{uuid.uuid4().hex}{generated_image_extension()}"
        temp_filepath = os.path.join(settings.TEMP_IMAGE_DIR, temp_filename)

        with open(temp_filepath, "wb") as f:
            f.write(image_data)

        temp_image_url = os.path.join(settings.MEDIA_URL, "temp_image", temp_filename)

        return JsonResponse(
            {
                "message": "Image generated!",
                "temp_image_url": temp_image_url,
                "temp_image_filename": temp_filename,
            }
        )

    except OpenAIConfigurationError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except (ValueError, ConnectionError, TimeoutError) as e:
        print("Exception!")
        print(e)
        return JsonResponse({"error": str(e)}, status=500)
