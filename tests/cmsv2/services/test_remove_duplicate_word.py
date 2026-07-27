"""
Tests for deleting a duplicate ``Word`` row (issue #531).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services import remove_duplicate_word


@pytest.fixture
def job() -> Job:
    return Job.objects.create(name="Tischler")


@pytest.fixture
def unit_a(job: Job) -> Unit:
    unit = Unit.objects.create(title="Werkzeuge")
    unit.jobs.add(job)
    return unit


@pytest.fixture
def unit_b(job: Job) -> Unit:
    unit = Unit.objects.create(title="Baustelle")
    unit.jobs.add(job)
    return unit


@pytest.mark.django_db()
def test_completeness_score_prefers_more_complete_word() -> None:
    bare = Word.objects.create(singular_article=1, word="Hammer")
    rich = Word.objects.create(
        singular_article=1,
        word="Hammer",
        definition="Ein Werkzeug",
        example_sentence="Der Hammer liegt auf der Werkbank.",
        example_sentence_check_status=CheckStatus.CONFIRMED,
    )
    assert remove_duplicate_word.completeness_score(
        rich
    ) > remove_duplicate_word.completeness_score(bare)


@pytest.mark.django_db()
def test_prepare_removal_finds_units_the_keeper_does_not_cover(
    unit_a: Unit, unit_b: Unit
) -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_a, word=keeper)
    UnitWordRelation.objects.create(unit=unit_b, word=loser)

    preview = remove_duplicate_word.prepare_removal(keeper, loser)

    assert [unit.pk for unit in preview.extra_units] == [unit_b.pk]


@pytest.mark.django_db()
def test_prepare_removal_empty_when_keeper_already_covers_everything(
    unit_a: Unit,
) -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_a, word=keeper)
    UnitWordRelation.objects.create(unit=unit_a, word=loser)

    preview = remove_duplicate_word.prepare_removal(keeper, loser)

    assert preview.extra_units == []


@pytest.mark.django_db()
def test_prepare_removal_empty_when_loser_has_no_units_at_all() -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")

    preview = remove_duplicate_word.prepare_removal(keeper, loser)

    assert preview.extra_units == []


@pytest.mark.django_db()
def test_prepare_removal_is_read_only(unit_a: Unit) -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_a, word=loser)

    remove_duplicate_word.prepare_removal(keeper, loser)

    assert Word.objects.filter(pk=loser.pk).exists()
    assert not keeper.units.filter(pk=unit_a.pk).exists()


@pytest.mark.django_db()
def test_apply_removal_deletes_loser() -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")

    remove_duplicate_word.apply_removal(keeper, loser, set())

    assert not Word.objects.filter(pk=loser.pk).exists()
    assert Word.objects.filter(pk=keeper.pk).exists()


@pytest.mark.django_db()
def test_apply_removal_adds_keeper_to_requested_unit(unit_b: Unit) -> None:
    """The exact scenario the review page asks about: carry the unit over."""
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_b, word=loser)

    remove_duplicate_word.apply_removal(keeper, loser, {unit_b.pk})

    assert keeper.units.filter(pk=unit_b.pk).exists()
    assert not Word.objects.filter(pk=loser.pk).exists()


@pytest.mark.django_db()
def test_apply_removal_without_confirmation_drops_the_unit(unit_b: Unit) -> None:
    """Not selecting "yes" for a unit means the word is simply no longer in it."""
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_b, word=loser)

    remove_duplicate_word.apply_removal(keeper, loser, set())

    assert not keeper.units.filter(pk=unit_b.pk).exists()


@pytest.mark.django_db()
def test_apply_removal_ignores_unit_ids_not_actually_extra(
    unit_a: Unit, unit_b: Unit
) -> None:
    """A unit id outside prepare_removal's extra_units (e.g. stale form data)
    must not silently link the keeper to something unrelated."""
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_a, word=keeper)

    remove_duplicate_word.apply_removal(keeper, loser, {unit_b.pk})

    assert not keeper.units.filter(pk=unit_b.pk).exists()


@pytest.mark.django_db()
def test_apply_removal_does_not_duplicate_existing_relation(unit_a: Unit) -> None:
    keeper = Word.objects.create(singular_article=1, word="Hammer")
    loser = Word.objects.create(singular_article=1, word="Hammer")
    UnitWordRelation.objects.create(unit=unit_a, word=keeper)
    UnitWordRelation.objects.create(unit=unit_a, word=loser)

    remove_duplicate_word.apply_removal(keeper, loser, {unit_a.pk})

    assert UnitWordRelation.objects.filter(unit=unit_a, word=keeper).count() == 1
