import base64
import os
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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

    prompt = """Du bist Content-Manager für eine Vokabel-Lern-App namens "Lunes". Die App richtet sich an Zugewanderte, die in Deutschland eine Ausbildung machen oder bereits beruflich tätig sind. Sie lernen Deutsch als Fremdsprache und benötigen spezifischen Fachwortschatz, der in regulären Sprachkursen nicht vermittelt wird.

        Die App zeigt Fachbegriffe aus dem Berufsfeld in Form von Bildern. Alle Vokabeln werden einsprachig (nur auf Deutsch) vermittelt – durch realistische Fotos, die das Wort eindeutig visuell darstellen.
        
        Für die Bildsprache gelten folgende Vorgaben:
        - Es sollen realistische Fotos sein (keine Illustrationen, keine Renderings).
        - Das Bildmotiv muss eindeutig dem jeweiligen Fachbegriff zuzuordnen sein.
        - Es soll nur der relevante Gegenstand oder die relevante Handlung zu sehen sein.
        - Keine zusätzlichen Objekte, kein Text, neutraler Hintergrund (z.B. weiß oder freigestellt).
    """
    if unit_title:
        prompt += f"Der Begriff gehört zum Lernmodul: {unit_title}"
    prompt += f'Erstelle ein passendes realistisches Foto zur Vokabel: "{word_text}"'
    if additional_info:
        prompt += f"Zusätzliche Hinweise zur Bildgestaltung: {additional_info}"
    prompt += "Ziel ist es, dass die Vokabel durch das Bild eindeutig verstanden werden kann – auch ohne Text oder Erklärung."

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
