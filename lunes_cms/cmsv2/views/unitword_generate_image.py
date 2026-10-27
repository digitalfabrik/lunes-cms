from __future__ import annotations

import logging
import os

from django.contrib import admin
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.base import ContentFile
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from lunes_cms.cmsv2.admins.image_prompt_info import render_image_prompt_info
from lunes_cms.cmsv2.areas import visible_unit_word_relations
from lunes_cms.cmsv2.models.static import ImageSource
from lunes_cms.cmsv2.services.image_generation import image_prompt_context
from lunes_cms.cmsv2.utils import replace_file, safe_temp_path
from lunes_cms.core import settings

logger = logging.getLogger(__name__)


@login_required
@permission_required("cmsv2.change_unitwordrelation", raise_exception=True)
def unitword_generate_image(request: HttpRequest, unitword_id: int) -> HttpResponse:
    """
    Dedicated view for generating image for a specific Unit<>Word relation.
    """

    unitword_instance = get_object_or_404(
        visible_unit_word_relations(request.user).select_related("word", "unit"),
        pk=unitword_id,
    )
    context = admin.site.each_context(request)
    context.update(
        {
            "unitword_instance": unitword_instance,
            "prompt_info": render_image_prompt_info(
                image_prompt_context(
                    unitword_instance.word, unit=unitword_instance.unit
                ),
                preview_url=reverse(
                    "cmsv2:unitword_image_prompt_preview", args=[unitword_instance.pk]
                ),
            ),
            "temp_image_url": None,
        }
    )

    return render(request, "admin/unitword_generate_image.html", context)


@login_required
@permission_required("cmsv2.change_unitwordrelation", raise_exception=True)
@require_POST
def unitword_store_generated_image_permanently(
    request: HttpRequest, unitword_id: int
) -> HttpResponseRedirect:
    """
    Downloads and save the image to the Unittword instance's image field
    and redirects back to the edit view.
    """

    unitword_instance = get_object_or_404(
        visible_unit_word_relations(request.user).select_related("word", "unit"),
        pk=unitword_id,
    )
    temp_filename = request.POST.get("temp_filename")

    if not temp_filename:
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    temp_filepath = safe_temp_path(settings.TEMP_IMAGE_DIR, temp_filename)
    if not temp_filepath:
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    try:
        with open(temp_filepath, "rb") as f:
            # Keep the temp file's extension: the bytes are OpenAI's own
            # encode, and a wrong suffix would trigger a re-encode on save
            # that strips its provenance markings.
            suffix = os.path.splitext(temp_filepath)[1]
            content_file = ContentFile(
                f.read(),
                name=f'{unitword_instance.word.word.replace(" ", "_")}-{unitword_instance.unit.title.replace(" ", "_")}{suffix}',
            )
            replace_file(unitword_instance.image, content_file, save=False)
            unitword_instance.save(image_source=ImageSource.AI_LABELED)

        os.remove(temp_filepath)

        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)

    except (ValueError, FileNotFoundError, OSError) as e:
        logger.error("Storing a generated image failed: %s", e)
        return redirect("admin:cmsv2_word_change", object_id=unitword_instance.word.pk)
