import urllib
import uuid

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models import Word


@staff_member_required
def unitword_generate_image(request, word_id):
    """
    Dedicated view for generating audio for a specific Word instance.
    """

    word_instance = get_object_or_404(Word, pk=word_id)

    context = admin.site.each_context(request)
    context.update({
        "word_instance": word_instance,
        "word_text": word_instance.word,
        "temp_audio_url": None,
        "temp_audio_filename": None,
    })

    return render(request, "admin/unitword_generate_image.html", context)


# @staff_member_required
# @csrf_exempt
# @require_POST
# def unitword_store_generated_image_permanently(request, word_id):
#     """
#     Downloads and save the image to the Unittword instance's image field
#     and redirects back to the edit view.
#     """
#
#     unitword_instance = get_object_or_404(Word, pk=word_id)
#     image_url = request.POST.get("temp_image_url")
#
#     try:
#         with urllib.request.urlopen(image_url) as response:
#             if response.status != 200:
#                 raise Exception(f"Failed to download image: {response.status}")
#
#             image_data = response.read()
#
#         file_name = f"{uuid.uuid4()}.png"
#         word_instance.image.save(file_name, ContentFile(image_data), save=True)
#
#         return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)
#
#     except Exception as e:
#         print(f"Error storing generated image: {e}")
#         return redirect("admin:cmsv2_word_change", object_id=word_instance.pk)
