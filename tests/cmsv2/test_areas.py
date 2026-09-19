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
    pending_area_of_unit,
    scope_jobs,
    scope_units,
    scope_words,
    validate_job_area,
    validate_relation_area,
    validate_unit_jobs,
)
from lunes_cms.cmsv2.models import Area, AreaCode, Job, Unit, Word
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


@pytest.mark.django_db
def test_validate_job_area_rejects_a_job_with_a_shared_unit(area: Area) -> None:
    """A job whose units are shared with other jobs cannot enter an area."""
    job = Job.objects.create(name="Job")
    other_job = Job.objects.create(name="Other job")
    unit = _unit_with_job("Shared unit", job)
    unit.jobs.add(other_job)

    with pytest.raises(ValidationError):
        validate_job_area(job, area)


@pytest.mark.django_db
def test_validate_job_area_rejects_a_job_whose_word_is_used_elsewhere(
    area: Area,
) -> None:
    """A job whose words are used outside of it cannot enter an area."""
    job = Job.objects.create(name="Job")
    unit = _unit_with_job("Unit", job)
    elsewhere = _unit_with_job("Elsewhere", Job.objects.create(name="Other job"))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=unit, word=word)
    UnitWordRelation.objects.create(unit=elsewhere, word=word)

    with pytest.raises(ValidationError):
        validate_job_area(job, area)


@pytest.mark.django_db
def test_validate_job_area_allows_a_job_that_owns_its_content(area: Area) -> None:
    """A job whose units and words belong to it alone may enter an area."""
    job = Job.objects.create(name="Job")
    unit = _unit_with_job("Unit", job)
    UnitWordRelation.objects.create(unit=unit, word=_word("Hammer"))

    validate_job_area(job, area)
    validate_job_area(job, None)


@pytest.mark.django_db
def test_pending_area_of_unit_prefers_the_jobs_of_the_form(area: Area) -> None:
    """
    While a unit is being saved its jobs are not written yet, so the area comes
    from the jobs the form validated.
    """
    area_job = Job.objects.create(name="Area job", area=area)
    unit = Unit.objects.create(title="Unit")

    assert pending_area_of_unit(unit) is None

    unit.pending_jobs = [area_job]
    assert pending_area_of_unit(unit) == area


@pytest.mark.django_db
def test_validate_relation_area_allows_own_word_while_the_unit_is_created(
    area: Area,
) -> None:
    """
    Adding a word of the own area to a brand new unit of that area must pass,
    even though the unit has no job in the database yet.
    """
    area_job = Job.objects.create(name="Area job", area=area)
    existing_unit = _unit_with_job("Existing unit", area_job)
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=existing_unit, word=word)

    new_unit = Unit(title="New unit")
    new_unit.pending_jobs = [area_job]

    validate_relation_area(new_unit, word)


@pytest.mark.django_db
def test_validate_relation_area_rejects_foreign_word_while_the_unit_is_created(
    area: Area,
) -> None:
    """The same path still rejects a word of the main app."""
    area_job = Job.objects.create(name="Area job", area=area)
    main_unit = _unit_with_job("Main unit", Job.objects.create(name="Main job"))
    word = _word("Hammer")
    UnitWordRelation.objects.create(unit=main_unit, word=word)

    new_unit = Unit(title="New unit")
    new_unit.pending_jobs = [area_job]

    with pytest.raises(ValidationError):
        validate_relation_area(new_unit, word)


@pytest.mark.django_db
def test_an_area_can_have_several_codes(area: Area) -> None:
    """Codes belong to one area, and an area may hand out several of them."""
    first = AreaCode.objects.create(area=area, code="KOLPING1")
    second = AreaCode.objects.create(area=area, code="KOLPING2")

    assert set(area.codes.all()) == {first, second}
    assert str(first) == "KOLPING1"


@pytest.mark.django_db
def test_a_code_is_not_generated(area: Area) -> None:
    """A code is always typed in, so a new one starts out empty."""
    code = AreaCode(area=area)

    assert code.code == ""

    with pytest.raises(ValidationError):
        code.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_code",
    ["SHORT12", "kolping1", "KOLPING-1", "KOLPING 1", "KOLPING_1"],
)
def test_invalid_codes_are_rejected(area: Area, invalid_code: str) -> None:
    """A code is at least 8 digits and upper case letters, nothing else."""
    with pytest.raises(ValidationError):
        AreaCode(area=area, code=invalid_code).full_clean()


@pytest.mark.django_db
def test_a_code_belongs_to_a_single_area(area: Area) -> None:
    """The same code must not be handed out by two areas."""
    other_area = Area.objects.create(name="Other")
    AreaCode.objects.create(area=area, code="KOLPING1")

    with pytest.raises(ValidationError):
        AreaCode(area=other_area, code="KOLPING1").full_clean()


@pytest.mark.django_db
def test_codes_are_deleted_with_their_area(area: Area) -> None:
    """A code without its area is meaningless, so it goes with it."""
    AreaCode.objects.create(area=area, code="KOLPING1")

    area.delete()

    assert AreaCode.objects.count() == 0


#
# Branding (#988): a logo and the two hex colors that decorate an area's
# content in the app.
#


@pytest.mark.django_db
def test_branding_fields_are_optional(area: Area) -> None:
    """An area without any branding set is valid."""
    area.full_clean()

    assert area.logo.name == ""
    assert area.primary_color == ""
    assert area.secondary_color == ""
    assert area.additional_information == ""
    assert area.additional_information_url == ""


@pytest.mark.django_db
def test_a_valid_additional_information_url_is_accepted(area: Area) -> None:
    """A proper URL passes validation."""
    area.additional_information = "Free text about this area."
    area.additional_information_url = "https://example.com/info"

    area.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("invalid_url", ["not-a-link", "example.com"])
def test_an_invalid_additional_information_url_is_rejected(
    area: Area, invalid_url: str
) -> None:
    """Anything that is not a valid, absolute URL is rejected."""
    area.additional_information_url = invalid_url

    with pytest.raises(ValidationError):
        area.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize("valid_color", ["#990000", "#FFFFFF", "#000000", "#a1b2c3"])
def test_valid_hex_colors_are_accepted(area: Area, valid_color: str) -> None:
    """A 6-digit hex color, upper or lower case, passes validation."""
    area.primary_color = valid_color
    area.secondary_color = valid_color

    area.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_color",
    ["990000", "#99000", "#9900000", "#gggggg", "red", "#99 000"],
)
def test_invalid_hex_colors_are_rejected(area: Area, invalid_color: str) -> None:
    """Anything that is not exactly '#' followed by 6 hex digits is rejected."""
    area.primary_color = invalid_color

    with pytest.raises(ValidationError):
        area.full_clean()
