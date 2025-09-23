from django.urls import path

from . import views

app_name = "cmsv2"

urlpatterns = [
    path(
        "jobs/<int:job_id>/update-icon/", views.update_job_icon, name="update_job_icon"
    ),
    path(
        "words/<int:word_id>/generate-audio",
        views.word_generate_audio,
        name="word_generate_audio",
    ),
    path(
        "words/generate-audio-via-openai",
        views.word_generate_audio_via_openai,
        name="word_generate_audio_via_openai",
    ),
    path(
        "words/generate-image-via-openai",
        views.generate_image_via_openai,
        name="generate_image_via_openai",
    ),
    path(
        "words/<int:word_id>/generate-image",
        views.word_generate_image,
        name="word_generate_image",
    ),
    path(
        "words/<int:word_id>/store-generated-audio-permanently",
        views.word_store_generated_audio_permanently,
        name="word_store_generated_audio_permanently",
    ),
    path(
        "words/<int:word_id>/store-generated-image-permanently",
        views.word_store_generated_image_permanently,
        name="word_store_generated_image_permanently",
    ),
    path(
        "words/<int:word_id>/update-image/",
        views.update_word_image,
        name="update_word_image",
    ),
    path(
        "words/<int:word_id>/update-audio/",
        views.update_word_audio,
        name="update_word_audio",
    ),
    path(
        "words/<int:word_id>/update-audio-check-status/",
        views.update_word_audio_check_status,
        name="update_word_audio_check_status",
    ),
    path(
        "words/<int:word_id>/update-image-check-status/",
        views.update_word_image_check_status,
        name="update_word_image_check_status",
    ),
    path(
        "units/<int:unit_id>/update-icon/",
        views.update_unit_icon,
        name="update_unit_icon",
    ),
    path(
        "unitwordrelations/<int:unitword_id>/update-image/",
        views.update_unitword_image,
        name="update_unitword_image",
    ),
    path(
        "unitwords/<int:unitword_id>/update-image-check-status/",
        views.update_unitword_image_check_status,
        name="update_unitword_image_check_status",
    ),
    path(
        "unitwordrelations/<int:unitword_id>/generate-image/",
        views.unitword_generate_image,
        name="unitword_generate_image",
    ),
    path(
        "unitwordrelations/<int:unitword_id>/store-generated-image-permanently/",
        views.unitword_store_generated_image_permanently,
        name="unitword_store_generated_image_permanently",
    ),
]
