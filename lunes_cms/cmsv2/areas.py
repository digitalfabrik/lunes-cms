"""
Area scoping and the invariants that keep the content of an area separate.

The area of a job is stored on :class:`~lunes_cms.cmsv2.models.job.Job`, every
other area membership is derived from it: a unit belongs to the area of its job
and a word to the area of the units it is linked to. This module is the single
place that knows how that derivation works, so admins, views and the API can
share it.
"""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Area, Job, Unit, Word

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet

    User = AbstractBaseUser | AnonymousUser


def administered_areas(user: "User") -> "QuerySet[Area]":
    """
    The areas the given user administers.

    :param user: The user in question
    :return: The queryset of areas the user administers
    """
    if not user.is_authenticated:
        return Area.objects.none()
    return Area.objects.filter(admins__pk=user.pk)


def is_area_admin(user: "User") -> bool:
    """
    Whether the given user administers at least one area.

    :param user: The user in question
    :return: Whether the user is the administrator of any area
    """
    return administered_areas(user).exists()


def scope_jobs(queryset: "QuerySet[Job]", user: "User") -> "QuerySet[Job]":
    """
    Restrict a job queryset to what the given user may see.

    Superusers see everything, administrators of an area see the jobs of the
    areas they administer, and everybody else sees only the jobs of the main
    app, which are the ones without an area.

    :param queryset: The job queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    areas = administered_areas(user)
    if areas.exists():
        return queryset.filter(area__in=areas)
    return queryset.filter(area__isnull=True)


def scope_units(queryset: "QuerySet[Unit]", user: "User") -> "QuerySet[Unit]":
    """
    Restrict a unit queryset to what the given user may see.

    The area of a unit is the area of its job, see :func:`scope_jobs` for the
    rules. Units without any job at all count as main app content.

    :param queryset: The unit queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    areas = administered_areas(user)
    if areas.exists():
        return queryset.filter(jobs__area__in=areas).distinct()
    return queryset.exclude(jobs__area__isnull=False).distinct()


def scope_words(queryset: "QuerySet[Word]", user: "User") -> "QuerySet[Word]":
    """
    Restrict a word queryset to what the given user may see.

    The area of a word is the area of the units it is linked to. A word that is
    not linked to any unit yet has no derivable area, so it stays visible to
    the main app and, additionally, to the area administrator who created it —
    otherwise a word created in the add popup of a unit that was then abandoned
    would be lost to its creator.

    :param queryset: The word queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    areas = administered_areas(user)
    if areas.exists():
        return queryset.filter(
            Q(units__jobs__area__in=areas)
            | Q(units__isnull=True, created_by_user__pk=user.pk)
        ).distinct()
    return queryset.exclude(units__jobs__area__isnull=False).distinct()


def area_of_unit(unit: Unit) -> Area | None:
    """
    The area a unit belongs to, derived from its job.

    :param unit: The unit in question
    :return: The area of the unit, or ``None`` for main app content
    """
    if not unit.pk:
        return None
    job = unit.jobs.filter(area__isnull=False).select_related("area").first()
    return job.area if job else None


def area_of_word(word: Word) -> Area | None:
    """
    The area a word belongs to, derived from the units it is linked to.

    :param word: The word in question
    :return: The area of the word, or ``None`` for main app content
    """
    if not word.pk:
        return None
    unit = word.units.filter(jobs__area__isnull=False).first()
    return area_of_unit(unit) if unit else None


def _other_areas_of_word(word: Word, unit: Unit) -> set[Area | None]:
    """
    The areas of all units of a word, except the given unit.

    :param word: The word whose units are inspected
    :param unit: The unit to leave out
    :return: The set of areas, where ``None`` stands for main app content
    """
    if not word.pk:
        return set()
    other_units = word.units.all()
    if unit.pk:
        other_units = other_units.exclude(pk=unit.pk)
    return {area_of_unit(other_unit) for other_unit in other_units}


def validate_unit_jobs(unit: Unit, jobs: Iterable[Job]) -> None:
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
    areas = {job.area for job in jobs if job.area_id}
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


def validate_relation_area(unit: Unit, word: Word) -> None:
    """
    Check that a word may be linked to a unit.

    All units of a word have to belong to the same area, so a word of the main
    app cannot be added to a unit of an area and vice versa.

    :param unit: The unit the word is about to be linked to
    :param word: The word that is about to be linked
    :raises ~django.core.exceptions.ValidationError: If the link would mix areas
    """
    target_area = area_of_unit(unit)
    if any(area != target_area for area in _other_areas_of_word(word, unit)):
        raise ValidationError(
            _(
                'The word "%(word)s" belongs to another area and cannot be used '
                "in this unit."
            )
            % {"word": word}
        )
