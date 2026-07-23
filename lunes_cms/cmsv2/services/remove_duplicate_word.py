"""
Removing a duplicate ``Word`` row (issue #531).

The kept word's own content is never touched — this is a straight deletion
of the duplicate, not a content merge. The only thing that needs a decision
is units: if the word being deleted belongs to a unit the kept word doesn't,
deleting it outright would silently make the word disappear from that unit
(the delete cascades its ``UnitWordRelation`` rows). So for each such unit,
the admin explicitly chooses whether the kept word should be added to it.

``prepare_removal`` is a pure, read-only computation of which units need a
decision (safe to call from a GET request rendering the review page), and
``apply_removal`` performs the actual write, given the admin's answers.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from ..models import Word
from ..models.static import CheckStatus
from ..models.unit import Unit, UnitWordRelation


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
    if word.definition and word.definition.strip():
        score += 1
    if word.additional_meaning_1 and word.additional_meaning_1.strip():
        score += 1
    if word.additional_meaning_2 and word.additional_meaning_2.strip():
        score += 1
    if word.plural and word.plural.strip():
        score += 1
    if word.grammatical_gender is not None:
        score += 1
    return score


@dataclass
class RemovalPreview:
    """What removing ``loser`` (keeping ``keeper``) would do, as computed by ``prepare_removal``."""

    keeper: Word
    loser: Word
    #: Units the loser belongs to that the keeper doesn't — each needs a yes/no decision.
    extra_units: list[Unit]


def prepare_removal(keeper: Word, loser: Word) -> RemovalPreview:
    """
    Compute which of the loser's units the keeper doesn't already cover.
    Read-only — never writes to the database.
    """
    keeper_unit_ids = set(keeper.units.values_list("pk", flat=True))
    extra_units = list(loser.units.exclude(pk__in=keeper_unit_ids).order_by("title"))
    return RemovalPreview(keeper=keeper, loser=loser, extra_units=extra_units)


@transaction.atomic
def apply_removal(keeper: Word, loser: Word, add_to_unit_ids: set[int]) -> None:
    """
    Delete ``loser``. For every id in ``add_to_unit_ids`` (expected to be a
    subset of ``prepare_removal(...).extra_units``), link ``keeper`` to that
    unit first, so the word doesn't disappear from it.
    """
    preview = prepare_removal(keeper, loser)
    valid_unit_ids = {unit.pk for unit in preview.extra_units}
    for unit_id in add_to_unit_ids & valid_unit_ids:
        UnitWordRelation.objects.get_or_create(unit_id=unit_id, word=keeper)
    loser.delete()
