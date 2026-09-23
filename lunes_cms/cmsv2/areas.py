"""
Area scoping and the invariants that keep the content of an area separate.

The area of a job is stored on :class:`~lunes_cms.cmsv2.models.job.Job`, every
other area membership is derived from it: a unit belongs to the area of its job
and a word to the area of the units it is linked to. Every job always belongs
to an area — the main app catalog is not the absence of an area but the one
area with ``is_main_app=True`` — so no code here needs a separate "no area"
case, see #1016. This module is the single place that knows how the
derivation works, so admins, views and the API can share it.

This module exposes three helper families: ``scope_*(queryset, user)`` narrows a
queryset the caller already holds, ``visible_*(user)`` narrows the whole table
the same way, and ``published_*(queryset, area)`` narrows to what the API serves
for an area token.
"""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models.area import Area

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet

    # Imported for the annotations only: importing the models package for real
    # would run into the import of this module in ``UnitWordRelation.clean()``.
    from .models import (
        AlternativeWord,
        Job,
        Unit,
        UnitWordRelation,
        Word,
    )

    User = AbstractBaseUser | AnonymousUser


def administered_areas(user: "User") -> "QuerySet[Area]":
    """
    The areas the given user administers, the main app area included — it is
    an ordinary area like any other from here on, see #1016.

    :param user: The user in question
    :return: The queryset of areas the user administers
    """
    if not user.is_authenticated:
        return Area.objects.none()
    return Area.objects.filter(admins__pk=user.pk)


def is_area_admin(user: "User") -> bool:
    """
    Whether the given user administers at least one area of a part organization.

    :param user: The user in question
    :return: Whether the user is the administrator of any such area
    """
    return administered_areas(user).exists()


def scope_jobs(queryset: "QuerySet[Job]", user: "User") -> "QuerySet[Job]":
    """
    Restrict a job queryset to what the given user may see.

    Superusers see everything, administrators of an area (the main app area
    included) see the jobs of the areas they administer, and everybody else
    sees nothing at all — a user who forgot to be assigned anywhere must not
    silently fall back to seeing the main app catalog, see #1016.

    :param queryset: The job queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    return queryset.filter(area__in=administered_areas(user))


def scope_units(queryset: "QuerySet[Unit]", user: "User") -> "QuerySet[Unit]":
    """
    Restrict a unit queryset to what the given user may see.

    The area of a unit is the area of its job, see :func:`scope_jobs` for the
    rules. A unit that is not linked to any job yet has no derivable area, so
    it stays visible only to the area administrator who created it — the
    same rule :func:`scope_words` applies to an unlinked word.

    :param queryset: The unit queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    if not user.is_authenticated:
        return queryset.none()
    areas = administered_areas(user)
    scoped = queryset.filter(jobs__area__in=areas)
    if areas.exists():
        scoped |= queryset.filter(jobs__isnull=True, created_by_user__pk=user.pk)
    return scoped.distinct()


def scope_words(queryset: "QuerySet[Word]", user: "User") -> "QuerySet[Word]":
    """
    Restrict a word queryset to what the given user may see.

    The area of a word is the area of the units it is linked to. A word that is
    not linked to any unit yet has no derivable area, so it stays visible only
    to the area administrator who created it — otherwise a word created in the
    add popup of a unit that was then abandoned would be lost to its creator.

    :param queryset: The word queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    if not user.is_authenticated:
        return queryset.none()
    areas = administered_areas(user)
    scoped = queryset.filter(units__jobs__area__in=areas)
    if areas.exists():
        scoped |= queryset.filter(units__isnull=True, created_by_user__pk=user.pk)
    return scoped.distinct()


def scope_unit_word_relations(
    queryset: "QuerySet[UnitWordRelation]", user: "User"
) -> "QuerySet[UnitWordRelation]":
    """
    Restrict a unit-word relation queryset to what the given user may see.

    The area of a relation is the area of its unit, see :func:`scope_units` for
    the rules.

    :param queryset: The relation queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    # pylint: disable=import-outside-toplevel
    from .models import Unit

    return queryset.filter(unit__in=scope_units(Unit.objects.all(), user))


def scope_alternative_words(
    queryset: "QuerySet[AlternativeWord]", user: "User"
) -> "QuerySet[AlternativeWord]":
    """
    Restrict an alternative word queryset to what the given user may see.

    An alternative word belongs to the area of the word it spells out, see
    :func:`scope_words` for the rules.

    :param queryset: The alternative word queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    # pylint: disable=import-outside-toplevel
    from .models import Word

    return queryset.filter(word__in=scope_words(Word.objects.all(), user))


def visible_jobs(user: "User") -> "QuerySet[Job]":
    """
    The jobs the given user may work with, see :func:`scope_jobs` for the rules.

    :param user: The user the jobs are restricted to
    :return: The restricted queryset
    """
    # pylint: disable=import-outside-toplevel
    from .models import Job

    return scope_jobs(Job.objects.all(), user)


def visible_units(user: "User") -> "QuerySet[Unit]":
    """
    The units the given user may work with, see :func:`scope_units` for the
    rules.

    :param user: The user the units are restricted to
    :return: The restricted queryset
    """
    # pylint: disable=import-outside-toplevel
    from .models import Unit

    return scope_units(Unit.objects.all(), user)


def visible_words(user: "User") -> "QuerySet[Word]":
    """
    The words the given user may work with, see :func:`scope_words` for the
    rules.

    :param user: The user the words are restricted to
    :return: The restricted queryset
    """
    # pylint: disable=import-outside-toplevel
    from .models import Word

    return scope_words(Word.objects.all(), user)


def visible_unit_word_relations(user: "User") -> "QuerySet[UnitWordRelation]":
    """
    The unit-word relations the given user may work with, see
    :func:`scope_unit_word_relations` for the rules.

    :param user: The user the relations are restricted to
    :return: The restricted queryset
    """
    # pylint: disable=import-outside-toplevel
    from .models import UnitWordRelation

    return scope_unit_word_relations(UnitWordRelation.objects.all(), user)


def visible_alternative_words(user: "User") -> "QuerySet[AlternativeWord]":
    """
    The alternative words the given user may work with, see
    :func:`scope_alternative_words` for the rules.

    :param user: The user the alternative words are restricted to
    :return: The restricted queryset
    """
    # pylint: disable=import-outside-toplevel
    from .models import AlternativeWord

    return scope_alternative_words(AlternativeWord.objects.all(), user)


def area_of_unit(unit: "Unit") -> Area | None:
    """
    The area a unit belongs to, derived from its job.

    :param unit: The unit in question
    :return: The area of the unit, or ``None`` if it belongs to no job yet
    """
    if not unit.pk:
        return None
    job = unit.jobs.select_related("area").first()
    return job.area if job else None


def _exclusive_area(area: Area | None) -> Area | None:
    """
    The area content is tied to *exclusively*, for the invariants below.

    The main app catalog is shared freely between its own many jobs, units
    and words — unlike a partner area, it owns nothing exclusively — so it
    counts the same as "no area" here, the same as it did before every job
    was required to have one, see #1016.

    :param area: The area in question
    :return: ``area`` itself, or ``None`` for the main app area or no area
    """
    if area is None or area.is_main_app:
        return None
    return area


def pending_area_of_unit(unit: "Unit") -> Area | None:
    """
    The exclusive area a unit is about to belong to.

    While a unit is being added or its jobs are being changed, the jobs of the
    unit are not written yet, so the area cannot be read from the database.
    :class:`~lunes_cms.cmsv2.admins.unit_admin.UnitAdminForm` puts the jobs it
    has validated on the instance, and this function prefers them over the
    stored ones.

    :param unit: The unit in question
    :return: The exclusive area the unit will belong to, or ``None`` (see
        :func:`_exclusive_area`)
    """
    jobs = getattr(unit, "pending_jobs", None)
    if jobs is None:
        return _exclusive_area(area_of_unit(unit))
    areas = {_exclusive_area(job.area) for job in jobs if job.area_id} - {None}
    return next(iter(areas), None)


def area_of_word(word: "Word") -> Area | None:
    """
    The area a word belongs to, derived from the units it is linked to.

    :param word: The word in question
    :return: The area of the word, or ``None`` if it belongs to no unit yet
    """
    if not word.pk:
        return None
    unit = word.units.filter(jobs__isnull=False).first()
    return area_of_unit(unit) if unit else None


def _other_areas_of_word(word: "Word", unit: "Unit") -> set[Area | None]:
    """
    The exclusive areas of all units of a word, except the given unit.

    :param word: The word whose units are inspected
    :param unit: The unit to leave out
    :return: The set of exclusive areas (see :func:`_exclusive_area`)
    """
    if not word.pk:
        return set()
    other_units = word.units.all()
    if unit.pk:
        other_units = other_units.exclude(pk=unit.pk)
    return {_exclusive_area(area_of_unit(other_unit)) for other_unit in other_units}


def validate_unit_jobs(unit: "Unit", jobs: "Iterable[Job]") -> None:
    """
    Check that the given jobs may be assigned to the given unit.

    A unit of a job that belongs to an area must not be assigned to any other
    job, and moving a unit into an area must not drag along words that are
    already used in another area.

    :param unit: The unit that is about to be saved
    :param jobs: The jobs the unit is about to be assigned to
    :raises ~django.core.exceptions.ValidationError: If the assignment would
                                                     mix areas
    """
    jobs = list(jobs)
    areas = {_exclusive_area(job.area) for job in jobs if job.area_id} - {None}
    if areas and len(jobs) > 1:
        raise ValidationError(
            _(
                "A unit of a job that belongs to an area must not be assigned "
                "to any other job."
            )
        )
    target_area = next(iter(areas), None)
    if not unit.pk:
        return
    for word in unit.words.all():
        if any(area != target_area for area in _other_areas_of_word(word, unit)):
            raise ValidationError(
                _(
                    'The word "%(word)s" is already used in another area, so this '
                    "unit cannot be assigned to these jobs."
                )
                % {"word": word}
            )


def validate_job_area(job: "Job", area: Area | None) -> None:
    """
    Check that a job may be moved into the given area.

    Everything below a job of a partner area belongs to that area alone, so a
    job whose units are shared with other jobs, or whose words are used
    outside of those units, cannot be moved into one. Untangling that content
    is a manual decision and is left to the content managers. Moving a job
    into the main app area is exempt: it is shared freely between its own
    jobs, so nothing needs to be untangled first.

    :param job: The job that is about to be saved
    :param area: The area the job is about to be moved into
    :raises ~django.core.exceptions.ValidationError: If the job shares content
    """
    if area is None or area.is_main_app or not job.pk:
        return
    for unit in job.units.prefetch_related("jobs", "words"):
        other_jobs = [other for other in unit.jobs.all() if other.pk != job.pk]
        if other_jobs:
            raise ValidationError(
                _(
                    'The unit "%(unit)s" is also assigned to %(jobs)s. A unit of '
                    "a job that belongs to an area must not be assigned to any "
                    "other job, so this job cannot be moved into an area."
                )
                % {
                    "unit": unit,
                    "jobs": ", ".join(str(other) for other in other_jobs),
                }
            )
        for word in unit.words.all():
            if word.units.exclude(jobs=job).exists():
                raise ValidationError(
                    _(
                        'The word "%(word)s" is also used outside of this job. '
                        "All words of an area belong to that area alone, so "
                        "this job cannot be moved into an area."
                    )
                    % {"word": word}
                )


def validate_relation_area(unit: "Unit", word: "Word") -> None:
    """
    Check that a word may be linked to a unit.

    All units of a word have to belong to the same area, so a word of one
    area cannot be added to a unit of another and vice versa.

    :param unit: The unit the word is about to be linked to
    :param word: The word that is about to be linked
    :raises ~django.core.exceptions.ValidationError: If the link would mix areas
    """
    target_area = pending_area_of_unit(unit)
    if any(area != target_area for area in _other_areas_of_word(word, unit)):
        raise ValidationError(
            _(
                'The word "%(word)s" belongs to another area and cannot be used '
                "in this unit."
            )
            % {"word": word}
        )


def published_jobs(queryset: "QuerySet[Job]", area: Area) -> "QuerySet[Job]":
    """
    Restrict a job queryset to what the API publishes for the given area.

    A client without an access token gets the jobs of the main app area, a
    client with a token gets the jobs of its own area and nothing else.
    Whether a job is released or archived is not decided here, the views
    keep that filter themselves.

    :param queryset: The job queryset to restrict
    :param area: The area of the client — the main app area for a client
        without an access token
    :return: The restricted queryset
    """
    return queryset.filter(area=area)


def published_units(queryset: "QuerySet[Unit]", area: Area) -> "QuerySet[Unit]":
    """
    Restrict a unit queryset to what the API publishes for the given area.

    The area of a unit is the area of its job, see :func:`published_jobs`.

    A unit that has *any* job outside the area asked for is rejected, rather
    than accepted because it has a job inside it too. A unit of a job of an
    area must not be assigned to any other job at all, so a unit that is, is
    broken data — but :func:`validate_unit_jobs` only runs in the admin, and a
    CSV import, a data migration or a shell session can write what the admin
    would refuse. The API is where such a mistake would turn into a leak, so
    it is rejected once more here.

    The exclude, rather than a second filter, is also what makes this safe
    across joins: a ``filter()`` on the jobs of a unit and the ``exclude()``
    below each open a join of their own, so the job that satisfies the
    caller's own filter (e.g. ``released``) need not be the job that
    satisfies the area condition here. Excluding the foreign jobs outright
    does not care which join matched.

    :param queryset: The unit queryset to restrict
    :param area: The area of the client — the main app area for a client
        without an access token
    :return: The restricted queryset
    """
    return (
        queryset.filter(jobs__area=area)
        .exclude(jobs__area__in=Area.objects.exclude(pk=area.pk))
        .distinct()
    )


def published_words(queryset: "QuerySet[Word]", area: Area) -> "QuerySet[Word]":
    """
    Restrict a word queryset to what the API publishes for the given area.

    The area of a word is the area of the units it is linked to, see
    :func:`published_units` for why an exclude is used rather than a filter.

    :param queryset: The word queryset to restrict
    :param area: The area of the client — the main app area for a client
        without an access token
    :return: The restricted queryset
    """
    return (
        queryset.filter(units__jobs__area=area)
        .exclude(units__jobs__area__in=Area.objects.exclude(pk=area.pk))
        .distinct()
    )
