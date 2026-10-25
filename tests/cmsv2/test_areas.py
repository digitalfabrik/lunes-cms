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
    default_area,
    is_area_admin,
    move_job_to_area,
    move_unit_to_area,
    scope_alternative_words,
    scope_jobs,
    scope_unit_word_relations,
    scope_units,
    scope_words,
    validate_job_area,
    validate_relation_area,
    validate_unit_area,
    validate_unit_jobs,
    validate_word_area,
)
from lunes_cms.cmsv2.models import AlternativeWord, Area, AreaCode, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _user(username: str, **kwargs: Any) -> User:
    return get_user_model().objects.create_user(username=username, **kwargs)


def _word(text: str, **kwargs: object) -> Word:
    return Word.objects.create(word=text, singular_article=1, **kwargs)


def _unit_with_job(title: str, job: Job) -> Unit:
    unit = Unit.objects.create(title=title, area=job.area)
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
def test_administered_areas_includes_the_main_app_area(main_app_area: Area) -> None:
    """
    The main app area is an ordinary area like any other from here on, so an
    administrator of it is recognized by ``administered_areas`` the same way.
    """
    admin_user = _user("main-app-admin")
    main_app_area.admins.add(admin_user)

    assert list(administered_areas(admin_user)) == [main_app_area]
    assert is_area_admin(admin_user) is True


@pytest.mark.django_db
def test_default_area_per_user_kind(area: Area, main_app_area: Area) -> None:
    """
    New content of an administrator of a single area goes into that area,
    everybody else creates main app content — unless they administer several
    areas without the main app, then it is the first of their own (#1061).
    """
    other_area = Area.objects.create(name="Other")
    single_area_admin = _user("single")
    area.admins.add(single_area_admin)
    multi_area_admin = _user("multi")
    area.admins.add(multi_area_admin)
    main_app_area.admins.add(multi_area_admin)
    partner_only_admin = _user("partner-only")
    area.admins.add(partner_only_admin)
    other_area.admins.add(partner_only_admin)
    superuser = _user("root", is_superuser=True)
    area.admins.add(superuser)

    assert default_area(single_area_admin) == area
    assert default_area(multi_area_admin) == main_app_area
    assert default_area(partner_only_admin) == area
    assert default_area(superuser) == main_app_area
    assert default_area(_user("plain")) == main_app_area


@pytest.mark.django_db
def test_scope_jobs_per_user_kind(area: Area, main_app_area: Area) -> None:
    """
    Superusers see every job, area administrators only the jobs of their area,
    administrators of the main app the jobs without an area, and a user who
    administers nothing at all sees nothing (#1016).
    """
    area_job = Job.objects.create(name="Area job", area=area)
    main_job = Job.objects.create(name="Main job", area=main_app_area)

    superuser = _user("root", is_superuser=True)
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    main_app_admin = _user("main-app-admin")
    main_app_area.admins.add(main_app_admin)
    plain_user = _user("plain")

    assert {area_job, main_job} <= set(scope_jobs(Job.objects.all(), superuser))
    assert set(scope_jobs(Job.objects.all(), admin_user)) == {area_job}
    main_app_jobs = set(scope_jobs(Job.objects.all(), main_app_admin))
    assert main_job in main_app_jobs
    assert area_job not in main_app_jobs
    assert set(scope_jobs(Job.objects.all(), plain_user)) == set()


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
def test_scope_units_per_user_kind(area: Area, main_app_area: Area) -> None:
    """
    Units are scoped by their own area, whether or not they are assigned to a
    job yet, and a unit without an area is visible to superusers only.
    """
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    jobless_area_unit = Unit.objects.create(title="Jobless area unit", area=area)
    main_unit = _unit_with_job(
        "Main unit", Job.objects.create(name="M", area=main_app_area)
    )

    superuser = _user("root", is_superuser=True)
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    main_app_admin = _user("main-app-admin")
    main_app_area.admins.add(main_app_admin)
    plain_user = _user("plain")

    assert {area_unit, jobless_area_unit, main_unit} <= set(
        scope_units(Unit.objects.all(), superuser)
    )
    assert set(scope_units(Unit.objects.all(), admin_user)) == {
        area_unit,
        jobless_area_unit,
    }
    main_app_units = set(scope_units(Unit.objects.all(), main_app_admin))
    assert main_unit in main_app_units
    assert area_unit not in main_app_units
    assert set(scope_units(Unit.objects.all(), plain_user)) == set()


@pytest.mark.django_db
def test_scope_words_per_user_kind(area: Area, main_app_area: Area) -> None:
    """
    Words are scoped by their own area, whether or not they are used in a unit yet.
    """
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    area_word = _word("Bereichswort", area=area)
    UnitWordRelation.objects.create(unit=area_unit, word=area_word)
    unlinked_area_word = _word("Frisch", area=area)
    main_word = _word("Hauptwort", area=main_app_area)

    superuser = _user("root", is_superuser=True)
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    main_app_admin = _user("main-app-admin")
    main_app_area.admins.add(main_app_admin)
    plain_user = _user("plain")

    assert {area_word, unlinked_area_word, main_word} <= set(
        scope_words(Word.objects.all(), superuser)
    )
    assert set(scope_words(Word.objects.all(), admin_user)) == {
        area_word,
        unlinked_area_word,
    }
    main_app_words = set(scope_words(Word.objects.all(), main_app_admin))
    assert main_word in main_app_words
    assert area_word not in main_app_words
    assert set(scope_words(Word.objects.all(), plain_user)) == set()


@pytest.mark.django_db
def test_scope_jobs_units_words_hide_everything_from_a_user_without_any_area(
    area: Area, main_app_area: Area
) -> None:
    """
    A user assigned to no area at all — neither a part organization's nor the
    main app's — must see nothing, so forgetting to assign one never silently
    grants the whole catalog (#1016).
    """
    Job.objects.create(name="Area job", area=area)
    Job.objects.create(name="Main job", area=main_app_area)
    Unit.objects.create(title="Unit", area=area)
    _word("Wort", area=area)
    plain_user = _user("plain")

    assert not scope_jobs(Job.objects.all(), plain_user).exists()
    assert not scope_units(Unit.objects.all(), plain_user).exists()
    assert not scope_words(Word.objects.all(), plain_user).exists()


@pytest.mark.django_db
def test_unlinked_content_is_shared_by_all_administrators_of_its_area(
    area: Area,
) -> None:
    """
    A word or unit that is not linked to anything yet is visible to every
    administrator of its area, not only to whoever created it, so a colleague
    can carry on working on it (#1061).
    """
    author = _user("author")
    colleague = _user("colleague")
    area.admins.add(author, colleague)
    word = _word("Entwurf", area=area, created_by_user=author)
    unit = Unit.objects.create(title="Entwurf", area=area, created_by_user=author)

    assert word in scope_words(Word.objects.all(), colleague)
    assert unit in scope_units(Unit.objects.all(), colleague)


@pytest.mark.django_db
def test_scope_unit_word_relations_per_user_kind(
    area: Area, main_app_area: Area
) -> None:
    """
    A relation inherits the area of its unit, and a user who administers no
    area at all sees nothing (#1016).
    """
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    main_unit = _unit_with_job(
        "Main unit", Job.objects.create(name="M", area=main_app_area)
    )
    area_relation = UnitWordRelation.objects.create(
        unit=area_unit, word=_word("Bereichswort", area=area)
    )
    main_relation = UnitWordRelation.objects.create(
        unit=main_unit, word=_word("Hauptwort", area=main_app_area)
    )

    superuser = _user("root", is_superuser=True)
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    main_app_admin = _user("main-app-admin")
    main_app_area.admins.add(main_app_admin)
    plain_user = _user("plain")

    # Only the area content is asserted exactly, the database may hold
    # fixture content of the main app as well.
    assert {area_relation, main_relation} <= set(
        scope_unit_word_relations(UnitWordRelation.objects.all(), superuser)
    )
    assert set(
        scope_unit_word_relations(UnitWordRelation.objects.all(), admin_user)
    ) == {area_relation}
    main_app_relations = set(
        scope_unit_word_relations(UnitWordRelation.objects.all(), main_app_admin)
    )
    assert main_relation in main_app_relations
    assert area_relation not in main_app_relations
    assert (
        set(scope_unit_word_relations(UnitWordRelation.objects.all(), plain_user))
        == set()
    )


@pytest.mark.django_db
def test_scope_alternative_words_per_user_kind(area: Area, main_app_area: Area) -> None:
    """
    An alternative word inherits the area of the word it spells out, and a
    user who administers no area at all sees nothing (#1016).
    """
    area_alternative = AlternativeWord.objects.create(
        word=_word("Bereichswort", area=area), alt_word="Bereichsvariante"
    )
    main_alternative = AlternativeWord.objects.create(
        word=_word("Hauptwort", area=main_app_area), alt_word="Hauptvariante"
    )

    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    main_app_admin = _user("main-app-admin")
    main_app_area.admins.add(main_app_admin)
    plain_user = _user("plain")

    assert set(scope_alternative_words(AlternativeWord.objects.all(), admin_user)) == {
        area_alternative
    }
    main_app_alternatives = set(
        scope_alternative_words(AlternativeWord.objects.all(), main_app_admin)
    )
    assert main_alternative in main_app_alternatives
    assert area_alternative not in main_app_alternatives
    assert (
        set(scope_alternative_words(AlternativeWord.objects.all(), plain_user)) == set()
    )


@pytest.mark.django_db
def test_validate_unit_jobs_rejects_a_job_of_another_area(
    area: Area, main_app_area: Area
) -> None:
    """A unit can only be assigned to jobs of its own area."""
    main_job = Job.objects.create(name="Main job", area=main_app_area)

    with pytest.raises(ValidationError):
        validate_unit_jobs([main_job], area)
    with pytest.raises(ValidationError):
        validate_unit_jobs([main_job], None)
    validate_unit_jobs([main_job], main_app_area)


@pytest.mark.django_db
def test_validate_unit_jobs_rejects_second_job_for_area_unit(area: Area) -> None:
    """A unit of an area job must not be assigned to any other job."""
    first = Job.objects.create(name="First", area=area)
    second = Job.objects.create(name="Second", area=area)

    with pytest.raises(ValidationError):
        validate_unit_jobs([first, second], area)


@pytest.mark.django_db
def test_validate_unit_jobs_allows_several_jobs_of_the_main_app(
    main_app_area: Area,
) -> None:
    """Units of the main app keep their free sharing between jobs."""
    first = Job.objects.create(name="First", area=main_app_area)
    second = Job.objects.create(name="Second", area=main_app_area)

    validate_unit_jobs([first, second], main_app_area)


@pytest.mark.django_db
def test_validate_unit_area_rejects_a_unit_whose_word_is_used_elsewhere(
    area: Area, main_app_area: Area
) -> None:
    """
    The words of a unit move along with it, so a unit sharing a word with
    another unit cannot be moved into another area.
    """
    unit = Unit.objects.create(title="Unit", area=main_app_area)
    other_unit = Unit.objects.create(title="Other unit", area=main_app_area)
    word = _word("Hammer", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=word)
    UnitWordRelation.objects.create(unit=other_unit, word=word)

    with pytest.raises(ValidationError):
        validate_unit_area(unit, area)


@pytest.mark.django_db
def test_validate_unit_area_allows_a_unit_that_owns_its_words(
    area: Area, main_app_area: Area
) -> None:
    """A unit whose words are used nowhere else may be moved."""
    unit = Unit.objects.create(title="Unit", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=_word("Hammer", area=main_app_area))

    validate_unit_area(unit, area)
    validate_unit_area(Unit(title="New unit"), area)


@pytest.mark.django_db
def test_validate_word_area_rejects_a_word_used_in_a_unit_of_another_area(
    area: Area, main_app_area: Area
) -> None:
    """A word used in units has to stay in the area of those units."""
    unit = Unit.objects.create(title="Unit", area=main_app_area)
    word = _word("Hammer", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=word)

    with pytest.raises(ValidationError):
        validate_word_area(word, area)
    validate_word_area(word, main_app_area)


@pytest.mark.django_db
def test_validate_word_area_allows_an_unlinked_word(
    area: Area, main_app_area: Area
) -> None:
    """A word that is not used in any unit may be moved freely."""
    validate_word_area(_word("Hammer", area=main_app_area), area)


@pytest.mark.django_db
def test_validate_relation_area_rejects_word_of_the_main_app(
    area: Area, main_app_area: Area
) -> None:
    """A word of the main app cannot be added to a unit of an area."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))

    with pytest.raises(ValidationError):
        validate_relation_area(area_unit, _word("Hammer", area=main_app_area))


@pytest.mark.django_db
def test_validate_relation_area_rejects_word_of_another_area(area: Area) -> None:
    """A word of one area cannot be added to a unit of another area."""
    other_area = Area.objects.create(name="Other")
    own_unit = _unit_with_job("Own unit", Job.objects.create(name="A", area=area))

    with pytest.raises(ValidationError):
        validate_relation_area(own_unit, _word("Hammer", area=other_area))


@pytest.mark.django_db
def test_validate_relation_area_allows_word_of_the_same_area(area: Area) -> None:
    """
    Inside one area, a word may be used by several units, including a unit
    that is still being created and is not assigned to a job yet.
    """
    first_unit = _unit_with_job("First", Job.objects.create(name="A", area=area))
    word = _word("Hammer", area=area)
    UnitWordRelation.objects.create(unit=first_unit, word=word)

    validate_relation_area(Unit.objects.create(title="Second", area=area), word)
    validate_relation_area(Unit(title="New unit", area=area), word)


@pytest.mark.django_db
def test_relation_clean_rejects_mixed_areas(area: Area, main_app_area: Area) -> None:
    """``UnitWordRelation.clean()`` refuses to link a word across areas."""
    area_unit = _unit_with_job("Area unit", Job.objects.create(name="A", area=area))
    word = _word("Hammer", area=main_app_area)

    with pytest.raises(ValidationError):
        UnitWordRelation(unit=area_unit, word=word).clean()


@pytest.mark.django_db
def test_relation_clean_does_not_check_an_unchanged_saved_relation_again(
    area: Area, main_app_area: Area
) -> None:
    """
    While a unit is being moved into another area, its saved relations still
    point at words of the old area, which are only moved along afterwards.
    """
    unit = Unit.objects.create(title="Unit", area=main_app_area)
    relation = UnitWordRelation.objects.create(
        unit=unit, word=_word("Hammer", area=main_app_area)
    )
    unit.area = area

    relation.unit = unit
    relation.clean()

    relation.word = _word("Zange", area=main_app_area)
    with pytest.raises(ValidationError):
        relation.clean()


@pytest.mark.django_db
def test_validate_job_area_rejects_a_job_with_a_shared_unit(
    area: Area, main_app_area: Area
) -> None:
    """A job whose units are shared with other jobs cannot enter an area."""
    job = Job.objects.create(name="Job", area=main_app_area)
    other_job = Job.objects.create(name="Other job", area=main_app_area)
    unit = _unit_with_job("Shared unit", job)
    unit.jobs.add(other_job)

    with pytest.raises(ValidationError):
        validate_job_area(job, area)


@pytest.mark.django_db
def test_validate_job_area_rejects_a_job_whose_word_is_used_elsewhere(
    area: Area, main_app_area: Area
) -> None:
    """A job whose words are used outside of it cannot enter an area."""
    job = Job.objects.create(name="Job", area=main_app_area)
    unit = _unit_with_job("Unit", job)
    elsewhere = _unit_with_job(
        "Elsewhere", Job.objects.create(name="Other job", area=main_app_area)
    )
    word = _word("Hammer", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=word)
    UnitWordRelation.objects.create(unit=elsewhere, word=word)

    with pytest.raises(ValidationError):
        validate_job_area(job, area)


@pytest.mark.django_db
def test_validate_job_area_rejects_moving_shared_content_into_the_main_app(
    area: Area, main_app_area: Area
) -> None:
    """
    The words of a job move along with it, so a job whose word is shared with
    another job of its area cannot leave for the main app either, or that
    other job would be left with a word of the main app.
    """
    job = Job.objects.create(name="Job", area=area)
    elsewhere = _unit_with_job("Elsewhere", Job.objects.create(name="Other", area=area))
    word = _word("Hammer", area=area)
    UnitWordRelation.objects.create(unit=_unit_with_job("Unit", job), word=word)
    UnitWordRelation.objects.create(unit=elsewhere, word=word)

    with pytest.raises(ValidationError):
        validate_job_area(job, main_app_area)


@pytest.mark.django_db
def test_validate_job_area_allows_a_job_that_owns_its_content(
    area: Area, main_app_area: Area
) -> None:
    """A job whose units and words belong to it alone may be moved."""
    job = Job.objects.create(name="Job", area=main_app_area)
    unit = _unit_with_job("Unit", job)
    UnitWordRelation.objects.create(unit=unit, word=_word("Hammer", area=main_app_area))

    validate_job_area(job, area)
    validate_job_area(job, None)
    validate_job_area(job, main_app_area)


@pytest.mark.django_db
def test_move_job_to_area_moves_its_units_and_words_along(
    area: Area, main_app_area: Area
) -> None:
    """Moving a job takes its units and their words into the new area."""
    job = Job.objects.create(name="Job", area=main_app_area)
    unit = _unit_with_job("Unit", job)
    word = _word("Hammer", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=word)
    untouched = _word("Zange", area=main_app_area)

    job.area = area
    job.save()
    move_job_to_area(job)

    unit.refresh_from_db()
    word.refresh_from_db()
    untouched.refresh_from_db()
    assert unit.area == area
    assert word.area == area
    assert untouched.area == main_app_area


@pytest.mark.django_db
def test_move_unit_to_area_moves_its_words_along(
    area: Area, main_app_area: Area
) -> None:
    """Moving a unit takes its words into the new area."""
    unit = Unit.objects.create(title="Unit", area=main_app_area)
    word = _word("Hammer", area=main_app_area)
    UnitWordRelation.objects.create(unit=unit, word=word)

    unit.area = area
    unit.save()
    move_unit_to_area(unit)

    word.refresh_from_db()
    assert word.area == area


@pytest.mark.django_db
def test_only_one_area_can_be_the_main_app(main_app_area: Area) -> None:
    """A second area cannot also be marked as the main app."""
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Area.objects.create(name="Second main app", is_main_app=True)


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
