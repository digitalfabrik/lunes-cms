import base64
import os
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.services.image_generation import build_image_prompt
from lunes_cms.cmsv2.utils import get_openai_client, OpenAIConfigurationError
from lunes_cms.core import settings


@staff_member_required
@csrf_exempt
@require_POST
def generate_image_via_openai(request):
    """
    AJAX endpoint to generate image using OpenAI and save it temporarily.
    Returns the URL/path to the temporary file.
    """

    word_text = request.POST.get("word_text")
    if not word_text:
        return JsonResponse({"error": "No word_text provided."}, status=400)
    additional_info = request.POST.get("additional_info")
    unit_title = request.POST.get("unit_title")
    model = request.POST.get("model")
    if not model:
        return JsonResponse({"error": "No model provided."}, status=400)

    prompt = build_image_prompt(word_text, unit_title, additional_info)

    try:
        client = get_openai_client()

        if model == "gpt-image-1":
            response = client.images.generate(
                model=model, prompt=prompt, size="1024x1024", n=1
            )
        else:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                response_format="b64_json",
                size="1024x1024",
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
