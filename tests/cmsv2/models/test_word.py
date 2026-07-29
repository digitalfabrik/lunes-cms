"""
Tests for Word.save()'s check-status bookkeeping (issue #917).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import Word


@pytest.mark.django_db
def test_new_word_without_assets_defaults_to_not_checked_everywhere() -> None:
    """A freshly created word with no audio, image or example sentence must
    report NOT_CHECKED (not None) for all three check statuses, so the admin
    dropdown never silently falls back to displaying "Confirmed"."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    assert word.audio_check_status == "NOT_CHECKED"
    assert word.image_check_status == "NOT_CHECKED"
    assert word.example_sentence_check_status == "NOT_CHECKED"


@pytest.mark.django_db
def test_unrelated_save_does_not_reset_confirmed_example_sentence_status() -> None:
    """Saving a word again without touching its example sentence or audio
    must not disturb a manually confirmed check status."""
    word = Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )
    word.example_sentence_check_status = "CONFIRMED"
    word.save()

    word.plural = "Hämmer"
    word.save()

    word.refresh_from_db()
    assert word.example_sentence_check_status == "CONFIRMED"
    assert word.plural == "Hämmer"
