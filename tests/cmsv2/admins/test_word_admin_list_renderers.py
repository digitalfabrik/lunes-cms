"""
Tests for ``WordAdminListRenderersMixin.list_example_sentence`` (#823), added
when the example sentence and its audio were surfaced as their own column on
the word changelist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib import admin
from django.core.files.base import ContentFile
from pytest_django import Settings

from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import CheckStatus


@pytest.fixture
def word_admin() -> WordAdmin:
    return WordAdmin(Word, admin.site)


@pytest.fixture(autouse=True)
def media_root(settings: Settings, tmp_path: Path) -> None:
    """Isolate saved audio files from the real media directory."""
    settings.MEDIA_ROOT = str(tmp_path)


def test_list_example_sentence_hides_controls_without_sentence(
    db: None, word_admin: WordAdmin
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)

    html = str(word_admin.list_example_sentence(word))

    assert "example-sentence-check-status-select" not in html
    assert "example-sentence-hover-container" not in html
    assert 'class="example-sentence-edit-form" style="display: none;"' not in html


def test_list_example_sentence_shows_text_and_status_for_short_sentence(
    db: None, word_admin: WordAdmin
) -> None:
    word = Word.objects.create(
        word="Hammer",
        singular_article=1,
        example_sentence="Der Hammer ist schwer.",
        example_sentence_check_status=CheckStatus.CONFIRMED,
    )

    html = str(word_admin.list_example_sentence(word))

    assert "Der Hammer ist schwer." in html
    assert "example-sentence-details" not in html
    assert f'name="example_sentence_check_status_{word.pk}"' in html
    assert f'<option value="{CheckStatus.CONFIRMED}" selected>' in html


def test_list_example_sentence_truncates_long_sentence(
    db: None, word_admin: WordAdmin
) -> None:
    long_sentence = "Der Hammer liegt in der Werkzeugkiste neben der Zange."
    assert len(long_sentence) > 40
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence=long_sentence
    )

    html = str(word_admin.list_example_sentence(word))

    assert "example-sentence-details" in html
    assert long_sentence[:40] in html
    assert long_sentence in html


def test_list_example_sentence_escapes_html_in_sentence(
    db: None, word_admin: WordAdmin
) -> None:
    word = Word.objects.create(
        word="Hammer",
        singular_article=1,
        example_sentence="<script>alert('xss')</script>",
    )

    html = str(word_admin.list_example_sentence(word))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_list_example_sentence_renders_audio_player_when_present(
    db: None, word_admin: WordAdmin
) -> None:
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )
    word.example_sentence_audio.save(
        "sentence.mp3", ContentFile(b"audio-bytes"), save=True
    )

    html = str(word_admin.list_example_sentence(word))

    assert "audio-player-container" in html
    assert "minimal-audio-player" in html


def test_list_example_sentence_hides_audio_player_without_audio(
    db: None, word_admin: WordAdmin
) -> None:
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )

    html = str(word_admin.list_example_sentence(word))

    assert "audio-player-container" not in html
    assert "add-example-sentence-audio-btn" in html
