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
from django.test import Client, RequestFactory
from django.urls import reverse
from PIL import Image
from pytest_django.fixtures import SettingsWrapper

from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.utils import is_ajax
from lunes_cms.core import settings as core_settings


@pytest.fixture
def media_dirs(
    settings: SettingsWrapper, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Isolate stored files and the temp directories the store views read from."""
    settings.MEDIA_ROOT = str(tmp_path)
    temp_image_dir = tmp_path / "temp_image"
    temp_audio_dir = tmp_path / "temp_audio"
    temp_image_dir.mkdir()
    temp_audio_dir.mkdir()
    monkeypatch.setattr(core_settings, "TEMP_IMAGE_DIR", str(temp_image_dir))
    monkeypatch.setattr(core_settings, "TEMP_AUDIO_DIR", str(temp_audio_dir))
    return temp_image_dir, temp_audio_dir


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
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
    assert reverse("cmsv2:word_generate_audio_via_openai") in audio_html
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
