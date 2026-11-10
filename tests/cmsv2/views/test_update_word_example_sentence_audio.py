"""
Tests for the ``update_word_example_sentence_audio`` endpoint (#823), which
uploads and deletes the example sentence audio from the word changelist.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse
from pytest_django import Settings

from lunes_cms.cmsv2.models import Area, Word


@pytest.fixture(autouse=True)
def media_root(settings: Settings, tmp_path: Path) -> None:
    """Isolate saved audio files from the real media directory."""
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture(name="word")
def fixture_word(db: None) -> Word:
    return Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )


def _url(word: Word) -> str:
    return reverse("cmsv2:update_word_example_sentence_audio", args=[word.pk])


def _audio_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("sentence.mp3", b"ID3", content_type="audio/mpeg")


@pytest.mark.django_db
def test_uploads_audio(admin_client: Client, word: Word) -> None:
    response = admin_client.post(_url(word), {"action": "add", "audio": _audio_file()})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    word.refresh_from_db()
    assert word.example_sentence_audio
    assert not word.audio


@pytest.mark.django_db
def test_deletes_audio(admin_client: Client, word: Word) -> None:
    word.example_sentence_audio.save("sentence.mp3", ContentFile(b"ID3"))

    response = admin_client.post(_url(word), {"action": "delete"})

    assert response.status_code == 200
    word.refresh_from_db()
    assert not word.example_sentence_audio


@pytest.mark.django_db
def test_rejects_delete_without_audio(admin_client: Client, word: Word) -> None:
    response = admin_client.post(_url(word), {"action": "delete"})

    assert response.status_code == 400
    assert response.json()["status"] == "error"


@pytest.mark.django_db
def test_rejects_upload_without_file(admin_client: Client, word: Word) -> None:
    response = admin_client.post(_url(word), {"action": "add"})

    assert response.status_code == 400
    word.refresh_from_db()
    assert not word.example_sentence_audio


@pytest.mark.django_db
def test_rejects_upload_without_example_sentence(admin_client: Client) -> None:
    word = Word.objects.create(word="Zange", singular_article=2)

    response = admin_client.post(_url(word), {"action": "add", "audio": _audio_file()})

    assert response.status_code == 400
    word.refresh_from_db()
    assert not word.example_sentence_audio


@pytest.mark.django_db
def test_rejects_unknown_action(admin_client: Client, word: Word) -> None:
    response = admin_client.post(_url(word), {"action": "rename"})

    assert response.status_code == 400


@pytest.mark.django_db
def test_denies_user_without_change_permission(
    client_with_permissions: Callable[..., Client], word: Word
) -> None:
    response = client_with_permissions("view_word").post(
        _url(word), {"action": "add", "audio": _audio_file()}
    )

    assert response.status_code == 403
    word.refresh_from_db()
    assert not word.example_sentence_audio


@pytest.mark.django_db
def test_hides_word_outside_the_area_of_the_user(
    client_with_permissions: Callable[..., Client],
) -> None:
    foreign_word = Word.objects.create(
        word="Zange",
        singular_article=2,
        example_sentence="Die Zange liegt im Koffer.",
        area=Area.objects.create(name="Foreign"),
    )

    response = client_with_permissions("change_word").post(
        _url(foreign_word), {"action": "add", "audio": _audio_file()}
    )

    assert response.status_code == 404
    assert response.json()["status"] == "error"
    foreign_word.refresh_from_db()
    assert not foreign_word.example_sentence_audio
