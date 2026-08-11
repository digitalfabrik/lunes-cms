"""
Ranking duplicate ``Word`` rows by completeness (issue #531).

Deleting a duplicate itself goes through Django's regular admin delete view
for ``Word`` (see :mod:`lunes_cms.cmsv2.templates.admin.cmsv2.duplicated_vocabulary`),
not a dedicated one - so all it takes is a link, no extra view or service call.
"""

from __future__ import annotations

from ..models import Word
from ..models.static import CheckStatus


def completeness_score(word: Word) -> int:
    """
    Score how much information a word carries, used to suggest which of two
    duplicates to keep by default. Higher is more complete. Purely a
    suggestion surfaced to the admin, never applied without confirmation.
    """
    score = 0
    if word.image and word.image_check_status == CheckStatus.CONFIRMED:
        score += 3
    if word.audio and word.audio_check_status == CheckStatus.CONFIRMED:
        score += 3
    if (
        word.example_sentence
        and word.example_sentence.strip()
        and word.example_sentence_check_status == CheckStatus.CONFIRMED
    ):
        score += 2
        if word.example_sentence_audio:
            score += 1
    if word.pronunciation and word.pronunciation.strip():
        score += 1
    if word.plural and word.plural.strip():
        score += 1
    if word.grammatical_gender is not None:
        score += 1
    return score
