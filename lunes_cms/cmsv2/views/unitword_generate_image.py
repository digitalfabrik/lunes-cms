import os

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.core import settings


@staff_member_required
def unitword_generate_image(request, unitword_id):
    """
    Dedicated view for generating image for a specific Unit<>Word relation.
    """

    unitword_instance = get_object_or_404(UnitWordRelation, pk=unitword_id)

    context = admin.site.each_context(request)
    context.update(
        {
            "unitword_instance": unitword_instance,
            "temp_image_url": None,
        }
    )

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
    temp_filename = request.POST.get("temp_filename")

    if not temp_filename:
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    temp_filepath = os.path.join(settings.TEMP_IMAGE_DIR, temp_filename)

    if not os.path.exists(temp_filepath):
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    try:
        with open(temp_filepath, "rb") as f:
            content_file = ContentFile(
                f.read(),
                name=f'{unitword_instance.word.word.replace(" ", "_")}-{unitword_instance.unit.title.replace(" ", "_")}.png',
            )
            unitword_instance.image.save(content_file.name, content_file)

        os.remove(temp_filepath)

        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    except (ValueError, FileNotFoundError, OSError) as e:
        print(f"Error storing generated image: {e}")
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)
