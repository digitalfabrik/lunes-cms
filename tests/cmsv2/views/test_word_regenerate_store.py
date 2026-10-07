"""
Tests for the inline (re)generation store endpoints used on the word detail page.

These endpoints back issues #822 (show/keep the old or new asset) and #835
(regenerate right on the word page): they return JSON for AJAX requests and
otherwise fall back to the legacy redirect behaviour.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from django.contrib import admin
from django.core.files.base import ContentFile
from django.test import Client, RequestFactory
from django.urls import reverse
from PIL import Image

from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.utils import is_ajax


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
    return buf.getvalue()


def _webp_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="WEBP")
    return buf.getvalue()


def test_is_ajax_detects_xhr_header() -> None:
    factory = RequestFactory()
    assert is_ajax(factory.post("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"))
    assert not is_ajax(factory.post("/"))


def test_store_image_ajax_returns_json_and_saves(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    temp_image_dir, _ = media_dirs
    word = Word.objects.create(word="Hammer", singular_article=1)
    temp_name = "temp_image_keepme.png"
    (temp_image_dir / temp_name).write_bytes(_png_bytes())

    url = reverse("cmsv2:word_store_generated_image_permanently", args=[word.pk])
    response = admin_client.post(
        url, {"temp_filename": temp_name}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["image_url"]
    word.refresh_from_db()
    assert word.image
    # The temporary file is consumed once stored permanently.
    assert not (temp_image_dir / temp_name).exists()


def test_store_image_keeps_webp_extension(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    """
    OpenAI now encodes generated images as WebP; storing them under any other
    extension would make Word.save() re-encode them and strip the provenance
    markings (EU AI Act, issue #936).
    """
    temp_image_dir, _ = media_dirs
    word = Word.objects.create(word="Hammer", singular_article=1)
    temp_name = "temp_image_keepme.webp"
    (temp_image_dir / temp_name).write_bytes(_webp_bytes())

    url = reverse("cmsv2:word_store_generated_image_permanently", args=[word.pk])
    response = admin_client.post(
        url, {"temp_filename": temp_name}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
    )

    assert response.status_code == 200
    word.refresh_from_db()
    assert word.image.name is not None
    assert word.image.name.endswith(".webp")


def test_store_image_ajax_missing_temp_returns_400(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    url = reverse("cmsv2:word_store_generated_image_permanently", args=[word.pk])

    response = admin_client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_store_image_non_ajax_missing_temp_redirects(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    url = reverse("cmsv2:word_store_generated_image_permanently", args=[word.pk])

    response = admin_client.post(url)

    assert response.status_code == 302


def test_store_audio_ajax_missing_temp_returns_400(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    url = reverse("cmsv2:word_store_generated_audio_permanently", args=[word.pk])

    response = admin_client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_store_sentence_audio_ajax_missing_temp_returns_400(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )
    url = reverse(
        "cmsv2:word_store_generated_example_sentence_audio_permanently", args=[word.pk]
    )

    response = admin_client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_admin_methods_render_inline_regenerate_widget(db: None) -> None:
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )
    word_admin = WordAdmin(Word, admin.site)

    audio_html = str(word_admin.audio_generate(word))
    assert "inline-regenerate" in audio_html
    assert 'data-asset-type="audio"' in audio_html
    assert reverse("cmsv2:word_generate_audio_via_openai", args=[word.pk]) in audio_html
    assert (
        reverse("cmsv2:word_store_generated_audio_permanently", args=[word.pk])
        in audio_html
    )

    image_html = str(word_admin.image_generate(word))
    assert 'data-asset-type="image"' in image_html
    assert "regen-additional-info" in image_html
    assert reverse("cmsv2:generate_image_via_openai") in image_html

    sentence_html = str(word_admin.example_sentence_audio_generate(word))
    assert 'data-text-field="example_sentence_text"' in sentence_html
    assert (
        reverse(
            "cmsv2:word_store_generated_example_sentence_audio_permanently",
            args=[word.pk],
        )
        in sentence_html
    )


def test_admin_methods_prompt_to_save_for_unsaved_word(db: None) -> None:
    word_admin = WordAdmin(Word, admin.site)
    unsaved = Word(word="Hammer", singular_article=1)

    assert "inline-regenerate" not in str(word_admin.audio_generate(unsaved))
    assert "inline-regenerate" not in str(word_admin.image_generate(unsaved))


@pytest.mark.parametrize(
    "url_name",
    [
        "word_store_generated_audio_permanently",
        "word_store_generated_example_sentence_audio_permanently",
    ],
)
def test_store_audio_ignores_a_traversing_temp_filename(
    admin_client: Client,
    db: None,
    media_dirs: tuple[Path, Path],
    tmp_path: Path,
    url_name: str,
) -> None:
    """
    The temp filename comes from the request, so a crafted value must not be
    able to reach a file outside the temp directory.
    """
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"not yours")
    word = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.post(
        reverse(f"cmsv2:{url_name}", args=[word.pk]),
        {"temp_audio_filename": f"../{outside.name}"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    assert outside.exists()


def test_store_sentence_audio_replaces_the_previous_file(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    _, temp_audio_dir = media_dirs
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )
    word.example_sentence_audio.save("old.mp3", ContentFile(b"old"), save=True)
    old_name = word.example_sentence_audio.name
    assert old_name
    temp_name = "temp_sentence.mp3"
    (temp_audio_dir / temp_name).write_bytes(b"new")

    response = admin_client.post(
        reverse(
            "cmsv2:word_store_generated_example_sentence_audio_permanently",
            args=[word.pk],
        ),
        {"temp_audio_filename": temp_name},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    word.refresh_from_db()
    assert word.example_sentence_audio.name != old_name
    assert not word.example_sentence_audio.storage.exists(old_name)
    assert word.example_sentence_audio.read() == b"new"


def test_store_unitword_sentence_audio_replaces_the_previous_file(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    _, temp_audio_dir = media_dirs
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Werkzeuge")
    relation = UnitWordRelation.objects.create(
        unit=unit, word=word, example_sentence="Der Hammer ist schwer."
    )
    relation.example_sentence_audio.save("old.mp3", ContentFile(b"old"), save=True)
    old_name = relation.example_sentence_audio.name
    assert old_name
    temp_name = "temp_sentence.mp3"
    (temp_audio_dir / temp_name).write_bytes(b"new")

    response = admin_client.post(
        reverse(
            "cmsv2:unitword_store_generated_example_sentence_audio_permanently",
            args=[relation.pk],
        ),
        {"temp_audio_filename": temp_name},
    )

    assert response.status_code == 302
    relation.refresh_from_db()
    assert relation.example_sentence_audio.name != old_name
    assert not relation.example_sentence_audio.storage.exists(old_name)
    assert relation.example_sentence_audio.read() == b"new"


def test_store_image_replaces_the_previous_file_and_resets_check_status(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    temp_image_dir, _ = media_dirs
    word = Word.objects.create(word="Hammer", singular_article=1)
    word.image.save("Hammer.webp", ContentFile(_webp_bytes()), save=True)
    word.image_check_status = CheckStatus.CONFIRMED
    word.save()
    old_name = word.image.name
    assert old_name
    temp_name = "temp_image_new.webp"
    (temp_image_dir / temp_name).write_bytes(_webp_bytes())

    response = admin_client.post(
        reverse("cmsv2:word_store_generated_image_permanently", args=[word.pk]),
        {"temp_filename": temp_name},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    word.refresh_from_db()
    new_name = word.image.name
    assert new_name and new_name != old_name
    assert word.image.storage.exists(new_name)
    assert not word.image.storage.exists(old_name)
    assert word.image_check_status == CheckStatus.NOT_CHECKED


def test_store_unitword_image_replaces_the_previous_file_and_resets_check_status(
    admin_client: Client, db: None, media_dirs: tuple[Path, Path]
) -> None:
    temp_image_dir, _ = media_dirs
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Werkzeuge")
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    relation.image.save("Hammer-Werkzeuge.webp", ContentFile(_webp_bytes()), save=True)
    relation.image_check_status = CheckStatus.CONFIRMED
    relation.save()
    old_name = relation.image.name
    assert old_name
    temp_name = "temp_image_new.webp"
    (temp_image_dir / temp_name).write_bytes(_webp_bytes())

    response = admin_client.post(
        reverse("cmsv2:unitword_store_generated_image_permanently", args=[relation.pk]),
        {"temp_filename": temp_name},
    )

    assert response.status_code == 302
    relation.refresh_from_db()
    new_name = relation.image.name
    assert new_name and new_name != old_name
    assert relation.image.storage.exists(new_name)
    assert not relation.image.storage.exists(old_name)
    assert relation.image_check_status == CheckStatus.NOT_CHECKED
