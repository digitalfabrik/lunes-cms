import urllib
import uuid

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models.unit import UnitWordRelation


@staff_member_required
def unitword_generate_image(request, unitword_id):
    """
    Dedicated view for generating audio for a specific Word instance.
    """

    unitword_instance = get_object_or_404(UnitWordRelation, pk=unitword_id)

    context = admin.site.each_context(request)
    context.update({
        "unitword_instance": unitword_instance,
        "temp_image_url": None,
    })

    return render(request, "admin/unitword_generate_image.html", context)


@staff_member_required
@csrf_exempt
@require_POST
def unitword_store_generated_image_permanently(request, unitword_id):
    """
    Downloads and save the image to the Unittword instance's image field
    and redirects back to the edit view.
    """

    unitword_instance = get_object_or_404(UnitWordRelation, pk=unitword_id)
    image_url = request.POST.get("temp_image_url")

    try:
        with urllib.request.urlopen(image_url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download image: {response.status}")

            image_data = response.read()

        file_name = f"{uuid.uuid4()}.png"
        unitword_instance.image.save(file_name, ContentFile(image_data), save=True)

        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    except Exception as e:
        print(f"Error storing generated image: {e}")
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)
