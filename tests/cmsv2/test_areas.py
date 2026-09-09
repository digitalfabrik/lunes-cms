"""
Tests for the area scoping and the invariants that keep the content of an area
separate.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError

from lunes_cms.cmsv2.areas import (
    administered_areas,
    area_of_unit,
    area_of_word,
    is_area_admin,
    scope_jobs,
    scope_units,
    scope_words,
    validate_relation_area,
    validate_unit_jobs,
)
from lunes_cms.cmsv2.models import Area, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _user(username: str, **kwargs: Any) -> User:
    return get_user_model().objects.create_user(username=username, **kwargs)


def _word(text: str, **kwargs: object) -> Word:
    return Word.objects.create(word=text, singular_article=1, **kwargs)


def _unit_with_job(title: str, job: Job) -> Unit:
    unit = Unit.objects.create(title=title)
    unit.jobs.add(job)
    return unit


@pytest.fixture
def area(db: None) -> Area:
    return Area.objects.create(name="Kolping")


@pytest.mark.django_db
def test_administered_areas_and_is_area_admin(area: Area) -> None:
    """An area administrator is recognized by the areas they are listed in."""
    admin_user = _user("area-admin")
    other_user = _user("plain")
    area.admins.add(admin_user)

    assert list(administered_areas(admin_user)) == [area]
    assert is_area_admin(admin_user) is True
    assert list(administered_areas(other_user)) == []
    assert is_area_admin(other_user) is False
    assert is_area_admin(AnonymousUser()) is False


@pytest.mark.django_db
def test_scope_jobs_per_user_kind(area: Area) -> None:
    """
    Superusers see every job, area administrators only the jobs of their area
    and everybody else only the jobs of the main app.
    """
    area_job = Job.objects.create(name="Area job", area=area)
    main_job = Job.objects.create(name="Main job")

    superuser = _user("root", is_superuser=True)
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    plain_user = _user("plain")

    assert {area_job, main_job} <= set(scope_jobs(Job.objects.all(), superuser))
    assert set(scope_jobs(Job.objects.all(), admin_user)) == {area_job}
    plain_jobs = set(scope_jobs(Job.objects.all(), plain_user))
    assert main_job in plain_jobs
    assert area_job not in plain_jobs


@pytest.mark.django_db
def test_scope_jobs_hides_other_areas(area: Area) -> None:
    """An area administrator does not see the jobs of a different area."""
    other_area = Area.objects.create(name="Other")
    own_job = Job.objects.create(name="Own", area=area)
    Job.objects.create(name="Foreign", area=other_area)

    admin_user = _user("area-admin")
    area.admins.add(admin_user)

    assert set(scope_jobs(Job.objects.all(), admin_user)) == {own_job}


@pytest.mark.django_db
def test_scope_units_per_user_kind(area: Area) -> None:
    """Units inherit the area of their job, units without a job are main app."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="M"))
    jobless_unit = Unit.objects.create(title="Jobless unit")

    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    plain_user = _user("plain")

    assert set(scope_units(Unit.objects.all(), admin_user)) == {area_unit}
    plain_units = set(scope_units(Unit.objects.all(), plain_user))
    assert {main_unit, jobless_unit} <= plain_units
    assert area_unit not in plain_units


@pytest.mark.django_db
def test_scope_words_per_user_kind(area: Area) -> None:
    """Words inherit the area of the units they are linked to."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="M"))
    area_word = _word("Bereichswort")
    main_word = _word("Hauptwort")
    UnitWordRelation.objects.create(unit=area_unit, word=area_word)
    UnitWordRelation.objects.create(unit=main_unit, word=main_word)

    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    plain_user = _user("plain")

    assert set(scope_words(Word.objects.all(), admin_user)) == {area_word}
    plain_words = set(scope_words(Word.objects.all(), plain_user))
    assert main_word in plain_words
    assert area_word not in plain_words


@pytest.mark.django_db
def test_scope_words_keeps_own_unlinked_word_visible_to_area_admin(
    area: Area,
) -> None:
    """
    A word that is not linked to a unit yet has no derivable area, so it stays
    visible to the area administrator who created it.
    """
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    own_word = _word("Frisch", created_by_user=admin_user)
    foreign_word = _word("Fremd", created_by_user=_user("someone"))

    visible = set(scope_words(Word.objects.all(), admin_user))
    assert own_word in visible
    assert foreign_word not in visible


@pytest.mark.django_db
def test_area_of_unit_and_word(area: Area) -> None:
    """The area of a unit comes from its job, the one of a word from its unit."""
    unit = _unit_with_job("Unit", Job.objects.create(name="A", area=area))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=unit, word=word)

    assert area_of_unit(unit) == area
    assert area_of_word(word) == area
    assert area_of_unit(Unit.objects.create(title="Jobless")) is None
    assert area_of_word(_word("Unlinked")) is None


@pytest.mark.django_db
def test_validate_unit_jobs_rejects_second_job_for_area_unit(area: Area) -> None:
    """A unit of an area job must not be assigned to any other job."""
    area_job = Job.objects.create(name="Area job", area=area)
    main_job = Job.objects.create(name="Main job")
    unit = _unit_with_job("Unit", area_job)

    with pytest.raises(ValidationError):
        validate_unit_jobs(unit, [area_job, main_job])


@pytest.mark.django_db
def test_validate_unit_jobs_allows_several_jobs_without_area() -> None:
    """Units of the main app keep their free sharing between jobs."""
    first = Job.objects.create(name="First")
    second = Job.objects.create(name="Second")
    unit = _unit_with_job("Unit", first)

    validate_unit_jobs(unit, [first, second])


@pytest.mark.django_db
def test_validate_unit_jobs_rejects_word_used_in_another_area(area: Area) -> None:
    """
    Moving a unit into an area must not drag along a word that is already used
    in the main app.
    """
    area_job = Job.objects.create(name="Area job", area=area)
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="Main job"))
    shared_unit = Unit.objects.create(title="Shared unit")
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=main_unit, word=word)
    UnitWordRelation.objects.create(unit=shared_unit, word=word)

    with pytest.raises(ValidationError):
        validate_unit_jobs(shared_unit, [area_job])


@pytest.mark.django_db
def test_validate_relation_area_rejects_word_of_the_main_app(area: Area) -> None:
    """A word of the main app cannot be added to a unit of an area."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="M"))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=main_unit, word=word)

    with pytest.raises(ValidationError):
        validate_relation_area(area_unit, word)


@pytest.mark.django_db
def test_validate_relation_area_rejects_word_of_another_area(area: Area) -> None:
    """A word of one area cannot be added to a unit of another area."""
    other_area = Area.objects.create(name="Other")
    own_unit = _unit_with_job("Own unit", Job.objects.create(name="A", area=area))
    foreign_unit = _unit_with_job(
        "Foreign unit", Job.objects.create(name="B", area=other_area)
    )
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=foreign_unit, word=word)

    with pytest.raises(ValidationError):
        validate_relation_area(own_unit, word)


@pytest.mark.django_db
def test_validate_relation_area_allows_word_of_the_same_area(area: Area) -> None:
    """Inside one area, a word may be used by several units."""
    first_unit = _unit_with_job("First", Job.objects.create(name="A", area=area))
    second_unit = Unit.objects.create(title="Second")
    second_unit.jobs.add(Job.objects.get(name="A"))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=first_unit, word=word)

    validate_relation_area(second_unit, word)


@pytest.mark.django_db
def test_relation_clean_rejects_mixed_areas(area: Area) -> None:
    """``UnitWordRelation.clean()`` refuses to link a word across areas."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="M"))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=main_unit, word=word)

    with pytest.raises(ValidationError):
        UnitWordRelation(unit=area_unit, word=word).clean()
