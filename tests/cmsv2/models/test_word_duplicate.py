"""
Tests for the ``AcceptedWordDuplicate`` bookkeeping model (issue #531).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Word


@pytest.mark.django_db()
def test_str_shows_the_shared_word_text_once() -> None:
    """Every word in an accepted group has the same text by definition -
    that's what makes them duplicates - so it must be shown once, not
    "(der) Hammer, (der) Hammer" (issue #531)."""
    a = Word.objects.create(word="Hammer", singular_article=1)
    b = Word.objects.create(word="Hammer", singular_article=1)
    accepted = AcceptedWordDuplicate.objects.create()
    accepted.words.set([a, b])

    assert str(accepted) == "(der) Hammer"


@pytest.mark.django_db()
def test_str_empty_without_words() -> None:
    accepted = AcceptedWordDuplicate.objects.create()

    assert str(accepted) == ""


@pytest.mark.django_db()
def test_str_falls_back_to_listing_on_text_mismatch() -> None:
    """Not expected in practice - accepted groups are always same-text -
    but a mismatch must be surfaced, not silently hidden behind one word."""
    a = Word.objects.create(word="Hammer", singular_article=1)
    b = Word.objects.create(word="Nagel", singular_article=1)
    accepted = AcceptedWordDuplicate.objects.create()
    accepted.words.set([a, b])

    assert str(accepted) == f"{a}, {b}"
