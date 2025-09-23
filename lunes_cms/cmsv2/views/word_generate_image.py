import os

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models import Word
from lunes_cms.core import settings


@staff_member_required
def word_generate_image(request, word_id):
    """
    Dedicated view for generating image for a specific Word instance.
    """

    word_instance = get_object_or_404(Word, pk=word_id)

    context = admin.site.each_context(request)
    context.update(
        {
            "word_instance": word_instance,
            "word_text": word_instance.word,
            "temp_image_url": None,
        }
    )

    return render(request, "admin/word_generate_image.html", context)


@staff_member_required
@csrf_exempt
@require_POST
def word_store_generated_image_permanently(request, word_id):
    """
    Downloads and save the image to the Word instance's image field
    and redirects back to the edit view.
    """

    word_instance = get_object_or_404(Word, pk=word_id)
    temp_filename = request.POST.get("temp_filename")

    if not temp_filename:
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    temp_filepath = os.path.join(settings.TEMP_IMAGE_DIR, temp_filename)

    if not os.path.exists(temp_filepath):
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    try:
        with open(temp_filepath, "rb") as f:
            content_file = ContentFile(
                f.read(), name=f'{word_instance.word.replace(" ", "_")}.png'
            )
            word_instance.image.save(content_file.name, content_file)
        word_instance.save()

        os.remove(temp_filepath)

        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)

    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error storing generated image: {e}")
        return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)
