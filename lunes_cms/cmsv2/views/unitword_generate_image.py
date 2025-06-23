from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404

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