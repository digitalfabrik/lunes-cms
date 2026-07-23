"""
Tests for the ``AcceptedWordDuplicate`` bookkeeping model (issue #531).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Word


@pytest.mark.django_db()
def test_str_lists_the_accepted_words() -> None:
    a = Word.objects.create(word="Hammer", singular_article=1)
    b = Word.objects.create(word="Hammer", singular_article=1)
    accepted = AcceptedWordDuplicate.objects.create()
    accepted.words.set([a, b])

    assert str(accepted) == f"{a}, {b}"
