"""
Tests for detecting duplicate vocabulary within a profession (issue #531).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services import duplicate_words


def _make_unit(job: Job, title: str = "Werkzeuge") -> Unit:
    unit = Unit.objects.create(title=title)
    unit.jobs.add(job)
    return unit


def _link(unit: Unit, word: Word) -> UnitWordRelation:
    return UnitWordRelation.objects.create(unit=unit, word=word)


@pytest.mark.django_db()
def test_two_distinct_words_same_text_same_job_is_a_duplicate() -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    a = Word.objects.create(singular_article=1, word="Hammer")
    b = Word.objects.create(singular_article=1, word="Hammer")
    _link(unit, a)
    _link(unit, b)

    results = duplicate_words.find_duplicate_word_groups()

    assert len(results) == 1
    assert results[0].word_text == "Hammer"
    assert results[0].job_names == ["Tischler"]
    assert {w.pk for w in results[0].words} == {a.pk, b.pk}


@pytest.mark.django_db()
def test_same_text_across_different_jobs_is_not_a_duplicate() -> None:
    job_a = Job.objects.create(name="Tischler")
    job_b = Job.objects.create(name="Maurer")
    unit_a = _make_unit(job_a)
    unit_b = _make_unit(job_b, title="Baustelle")
    a = Word.objects.create(singular_article=1, word="Hammer")
    b = Word.objects.create(singular_article=1, word="Hammer")
    _link(unit_a, a)
    _link(unit_b, b)

    assert duplicate_words.find_duplicate_word_groups() == []


@pytest.mark.django_db()
def test_one_word_in_two_units_of_same_job_is_not_a_duplicate() -> None:
    """Same word taught in two contexts of one job is normal reuse, not a data problem."""
    job = Job.objects.create(name="Tischler")
    unit_1 = _make_unit(job, title="Werkzeuge")
    unit_2 = _make_unit(job, title="Baustelle")
    word = Word.objects.create(singular_article=1, word="Hammer")
    _link(unit_1, word)
    _link(unit_2, word)

    assert duplicate_words.find_duplicate_word_groups() == []


@pytest.mark.django_db()
def test_group_count_matches_unresolved_groups() -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    for text in ("Hammer", "Säge"):
        a = Word.objects.create(singular_article=1, word=text)
        b = Word.objects.create(singular_article=1, word=text)
        _link(unit, a)
        _link(unit, b)

    assert duplicate_words.duplicate_word_group_count() == 2


@pytest.mark.django_db()
def test_unit_shared_by_multiple_jobs_produces_a_single_group() -> None:
    """The exact bug this was designed to fix: a unit belonging to several
    jobs must not repeat the same duplicate group once per job — one group,
    listing every job it's reachable from."""
    job_a = Job.objects.create(name="Berufskraftfahrer/-in")
    job_b = Job.objects.create(name="Kfz-Mechatroniker/-in")
    unit = Unit.objects.create(title="Lichter")
    unit.jobs.add(job_a, job_b)
    a = Word.objects.create(singular_article=1, word="Abblendlicht")
    b = Word.objects.create(singular_article=1, word="Abblendlicht")
    _link(unit, a)
    _link(unit, b)

    results = duplicate_words.find_duplicate_word_groups()

    assert len(results) == 1
    assert results[0].job_names == ["Berufskraftfahrer/-in", "Kfz-Mechatroniker/-in"]
    assert {w.pk for w in results[0].words} == {a.pk, b.pk}


@pytest.mark.django_db()
def test_unassigned_word_folds_into_the_job_of_its_duplicate() -> None:
    """Exact real-world scenario: a second word created via the Word admin,
    not yet linked to any unit — must still show up under the job(s) the
    first, already-assigned copy belongs to."""
    job = Job.objects.create(name="Kfz-Mechatroniker/-in")
    unit = _make_unit(job, title="Lichter")
    # A distinctive, nonsense word text: the shared session-scoped fixture
    # data (tests/conftest.py's `load_test_data`) persists real vocabulary
    # across the whole test session without a per-test rollback — this
    # detection scans the entire Word table by design, so it would pick up
    # a real fixture job/word of the same name/text otherwise.
    assigned = Word.objects.create(singular_article=1, word="Flimmerquastenzange")
    orphan = Word.objects.create(singular_article=1, word="Flimmerquastenzange")
    _link(unit, assigned)
    # `orphan` deliberately has no UnitWordRelation at all.

    results = duplicate_words.find_duplicate_word_groups()

    assert len(results) == 1
    assert results[0].job_names == ["Kfz-Mechatroniker/-in"]
    assert {w.pk for w in results[0].words} == {assigned.pk, orphan.pk}


@pytest.mark.django_db()
def test_unassigned_word_shows_under_every_job_of_a_multi_job_duplicate() -> None:
    job_a = Job.objects.create(name="Kfz-Mechatroniker/-in")
    job_b = Job.objects.create(name="Berufskraftfahrer/-in")
    unit = Unit.objects.create(title="Lichter")
    unit.jobs.add(job_a, job_b)
    assigned = Word.objects.create(singular_article=1, word="Flimmerquastenzange")
    orphan = Word.objects.create(singular_article=1, word="Flimmerquastenzange")
    _link(unit, assigned)

    results = duplicate_words.find_duplicate_word_groups()

    assert len(results) == 1
    assert results[0].job_names == ["Berufskraftfahrer/-in", "Kfz-Mechatroniker/-in"]
    assert {w.pk for w in results[0].words} == {assigned.pk, orphan.pk}


@pytest.mark.django_db()
def test_two_unassigned_words_land_in_unassigned_bucket() -> None:
    """No job anywhere in the picture at all — nothing to attach the group to."""
    a = Word.objects.create(singular_article=1, word="Flimmerquastenzange")
    b = Word.objects.create(singular_article=1, word="Flimmerquastenzange")

    results = duplicate_words.find_duplicate_word_groups()

    assert len(results) == 1
    assert results[0].job_names == []
    assert {w.pk for w in results[0].words} == {a.pk, b.pk}


@pytest.mark.django_db()
def test_words_within_group_ordered_by_completeness_first() -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    bare = Word.objects.create(singular_article=1, word="Hammer")
    rich = Word.objects.create(
        singular_article=1,
        word="Hammer",
        definition="Ein Werkzeug",
        example_sentence="Der Hammer liegt auf der Werkbank.",
        example_sentence_check_status=CheckStatus.CONFIRMED,
    )
    _link(unit, bare)
    _link(unit, rich)

    results = duplicate_words.find_duplicate_word_groups()

    assert [w.pk for w in results[0].words] == [rich.pk, bare.pk]
