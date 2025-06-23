from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openai import OpenAI

from lunes_cms.core import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@staff_member_required
@csrf_exempt
@require_POST
def generate_image_via_openai(request):
    """
    AJAX endpoint to generate image using OpenAI and save it temporarily.
    Returns the URL/path to the temporary file.
    """

    word_text = request.POST.get("word_text")
    additional_info = request.POST.get("additional_info")
    unit_name = request.POST.get("unit_name")
    if not word_text:
        return JsonResponse({"error": "No word_text provided."}, status=400)

    prompt = f'''Du bist Content-Manager für eine Vokabel-Lern-App namens "Lunes". Die App richtet sich an Zugewanderte, die in Deutschland eine Ausbildung machen oder bereits beruflich tätig sind. Sie lernen Deutsch als Fremdsprache und benötigen spezifischen Fachwortschatz, der in regulären Sprachkursen nicht vermittelt wird.

        Die App zeigt Fachbegriffe aus dem Berufsfeld in Form von Bildern. Alle Vokabeln werden einsprachig (nur auf Deutsch) vermittelt – durch realistische Fotos, die das Wort eindeutig visuell darstellen.
        
        Für die Bildsprache gelten folgende Vorgaben:
        - Es sollen realistische Fotos sein (keine Illustrationen, keine Renderings).
        - Das Bildmotiv muss eindeutig dem jeweiligen Fachbegriff zuzuordnen sein.
        - Es soll nur der relevante Gegenstand oder die relevante Handlung zu sehen sein.
        - Keine zusätzlichen Objekte, kein Text, neutraler Hintergrund (z.B. weiß oder freigestellt).
    '''
    if unit_name:
        prompt += f'Der Begriff gehört zum Lernmodul: {unit_name}'
    prompt += f'Erstelle ein passendes realistisches Foto zur Vokabel: "{word_text}"'
    if additional_info:
        prompt += f'Zusätzliche Hinweise zur Bildgestaltung: {additional_info}'
    prompt += "Ziel ist es, dass die Vokabel durch das Bild eindeutig verstanden werden kann – auch ohne Text oder Erklärung."

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            n=1
        )

        return JsonResponse({
            "message": "Image generated!",
            "temp_image_url": response.data[0].url
        })

    except Exception as e:
        print("Exception!")
        print(e)
        return JsonResponse({"error": str(e)}, status=500)
