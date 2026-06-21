import os

from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.utils import is_ajax
from lunes_cms.core import settings


@staff_member_required
@csrf_exempt
@require_POST
def word_store_generated_image_permanently(request, word_id):
    """
    Saves the temporary image to the Word instance's image field.

    For AJAX requests (inline regeneration on the change page) it returns a
    JSON response; otherwise it redirects back to the edit view.
    """

    word_instance = get_object_or_404(Word, pk=word_id)
    temp_filename = request.POST.get("temp_filename")

    def failure(message, status=400):
        if is_ajax(request):
            return JsonResponse({"status": "error", "message": message}, status=status)
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    if not temp_filename:
        return failure("No temporary image file provided.")

    temp_filepath = os.path.join(settings.TEMP_IMAGE_DIR, temp_filename)

    if not os.path.exists(temp_filepath):
        return failure("Temporary image file no longer exists.")

    try:
        with open(temp_filepath, "rb") as f:
            content_file = ContentFile(
                f.read(), name=f'{word_instance.word.replace(" ", "_")}.png'
            )
            word_instance.image.save(content_file.name, content_file)
        word_instance.save()

        os.remove(temp_filepath)

        if is_ajax(request):
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Image saved successfully.",
                    "image_url": (
                        word_instance.image.url if word_instance.image else None
                    ),
                }
            )
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    except (ValueError, FileNotFoundError, OSError) as e:
        return failure(f"Error storing generated image: {e}", status=500)
