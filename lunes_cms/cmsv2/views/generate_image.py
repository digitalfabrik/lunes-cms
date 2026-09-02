from __future__ import annotations

import base64
import os
import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.services.image_generation import build_image_prompt
from lunes_cms.cmsv2.utils import get_openai_client, OpenAIConfigurationError
from lunes_cms.core import settings
from .decorators import require_any_permission_json


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


@login_required
@require_any_permission_json("cmsv2.change_word", "cmsv2.change_unitwordrelation")
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
        client = get_openai_client()

        # quality is an env-configured str (LUNES_CMS_OPENAI_IMAGE_QUALITY), which the
        # SDK's overloads can't statically narrow to their Literal[...] type.
        response = client.images.generate(
            model=settings.OPENAI_IMAGE_MODEL,
            prompt=prompt,
            size="1024x1024",
            quality=settings.OPENAI_IMAGE_QUALITY,  # type: ignore[call-overload]
            n=1,
        )

        b64_image = response.data[0].b64_json
        image_data = base64.b64decode(b64_image)

        os.makedirs(settings.TEMP_IMAGE_DIR, exist_ok=True)

        temp_filename = f"temp_image_{uuid.uuid4().hex}.png"
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
