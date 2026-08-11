"""
Tests for ranking duplicate ``Word`` rows by completeness (issue #531).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.services import remove_duplicate_word


@pytest.mark.django_db()
def test_completeness_score_prefers_more_complete_word() -> None:
    bare = Word.objects.create(singular_article=1, word="Hammer")
    rich = Word.objects.create(
        singular_article=1,
        word="Hammer",
        pronunciation="Hamer",
        example_sentence="Der Hammer liegt auf der Werkbank.",
        example_sentence_check_status=CheckStatus.CONFIRMED,
    )
    assert remove_duplicate_word.completeness_score(
        rich
    ) > remove_duplicate_word.completeness_score(bare)
