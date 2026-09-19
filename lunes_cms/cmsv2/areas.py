"""
Area scoping and the invariants that keep the content of an area separate.

The area of a job is stored on :class:`~lunes_cms.cmsv2.models.job.Job`, every
other area membership is derived from it: a unit belongs to the area of its job
and a word to the area of the units it is linked to. This module is the single
place that knows how that derivation works, so admins, views and the API can
share it.

This module exposes three helper families: ``scope_*(queryset, user)``
narrows a queryset the caller already holds, ``visible_*(user)`` narrows the
whole table the same way, and ``published_*(queryset, area)`` narrows to what
the API serves for an area token.
"""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models.alternative_word import AlternativeWord
from .models.area import Area
from .models.job import Job
from .models.unit import Unit, UnitWordRelation
from .models.word import Word

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser
    from django.db.models import QuerySet

    User = AbstractBaseUser | AnonymousUser


def administered_areas(user: "User") -> QuerySet[Area]:
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


def scope_jobs(queryset: QuerySet[Job], user: "User") -> QuerySet[Job]:
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


def scope_units(queryset: QuerySet[Unit], user: "User") -> QuerySet[Unit]:
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


def scope_words(queryset: QuerySet[Word], user: "User") -> QuerySet[Word]:
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


def scope_unit_word_relations(
    queryset: QuerySet[UnitWordRelation], user: "User"
) -> QuerySet[UnitWordRelation]:
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
    return queryset.filter(unit__in=scope_units(Unit.objects.all(), user))


def scope_alternative_words(
    queryset: QuerySet[AlternativeWord], user: "User"
) -> QuerySet[AlternativeWord]:
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
    return queryset.filter(word__in=scope_words(Word.objects.all(), user))


def visible_jobs(user: "User") -> QuerySet[Job]:
    """
    The jobs the given user may work with, see :func:`scope_jobs` for the rules.

    :param user: The user the jobs are restricted to
    :return: The restricted queryset
    """
    return scope_jobs(Job.objects.all(), user)


def visible_units(user: "User") -> QuerySet[Unit]:
    """
    The units the given user may work with, see :func:`scope_units` for the
    rules.

    :param user: The user the units are restricted to
    :return: The restricted queryset
    """
    return scope_units(Unit.objects.all(), user)


def visible_words(user: "User") -> QuerySet[Word]:
    """
    The words the given user may work with, see :func:`scope_words` for the
    rules.

    :param user: The user the words are restricted to
    :return: The restricted queryset
    """
    return scope_words(Word.objects.all(), user)


def visible_unit_word_relations(user: "User") -> QuerySet[UnitWordRelation]:
    """
    The unit-word relations the given user may work with.

    The word and the unit of a relation are selected along with it, see
    :func:`scope_unit_word_relations` for the rules.

    :param user: The user the relations are restricted to
    :return: The restricted queryset
    """
    return scope_unit_word_relations(
        UnitWordRelation.objects.select_related("word", "unit"), user
    )


def visible_alternative_words(user: "User") -> QuerySet[AlternativeWord]:
    """
    The alternative words the given user may work with, see
    :func:`scope_alternative_words` for the rules.

    :param user: The user the alternative words are restricted to
    :return: The restricted queryset
    """
    return scope_alternative_words(AlternativeWord.objects.all(), user)


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


def pending_area_of_unit(unit: Unit) -> Area | None:
    """
    The area a unit is about to belong to.

    While a unit is being added or its jobs are being changed, the jobs of the
    unit are not written yet, so the area cannot be read from the database.
    :class:`~lunes_cms.cmsv2.admins.unit_admin.UnitAdminForm` puts the jobs it
    has validated on the instance, and this function prefers them over the
    stored ones.

    :param unit: The unit in question
    :return: The area the unit will belong to, or ``None`` for main app content
    """
    jobs = getattr(unit, "pending_jobs", None)
    if jobs is None:
        return area_of_unit(unit)
    areas = {job.area for job in jobs if job.area_id}
    return next(iter(areas), None)


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


def validate_job_area(job: Job, area: Area | None) -> None:
    """
    Check that a job may be moved into the given area.

    Everything below a job of an area belongs to that area alone, so a job
    whose units are shared with other jobs, or whose words are used outside of
    those units, cannot be moved into an area. Untangling that content is a
    manual decision and is left to the content managers.

    :param job: The job that is about to be saved
    :param area: The area the job is about to be moved into
    :raises ~django.core.exceptions.ValidationError: If the job shares content
    """
    if area is None or not job.pk:
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


def validate_relation_area(unit: Unit, word: Word) -> None:
    """
    Check that a word may be linked to a unit.

    All units of a word have to belong to the same area, so a word of the main
    app cannot be added to a unit of an area and vice versa.

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


def published_jobs(queryset: QuerySet[Job], area: Area | None) -> QuerySet[Job]:
    """
    Restrict a job queryset to what the API publishes for the given area.

    A client without an access token gets the jobs of the main app, which are
    the ones without an area, a client with a token gets the jobs of its area
    and nothing else. Whether a job is released or archived is not decided
    here, the views keep that filter themselves.

    :param queryset: The job queryset to restrict
    :param area: The area of the client, or ``None`` for the main app
    :return: The restricted queryset
    """
    if area is None:
        return queryset.filter(area__isnull=True)
    return queryset.filter(area=area)


def published_units(queryset: QuerySet[Unit], area: Area | None) -> QuerySet[Unit]:
    """
    Restrict a unit queryset to what the API publishes for the given area.

    The area of a unit is the area of its job, see :func:`published_jobs`.

    Both branches reject a unit that has *any* job outside the area asked for,
    rather than accepting one that has a job inside it. A unit of a job of an
    area must not be assigned to any other job at all, so a unit that is, is
    broken data — but :func:`validate_unit_jobs` only runs in the admin, and a
    CSV import, a data migration or a shell session can write what the admin
    would refuse. The API is where such a mistake would turn into a leak, so
    it is rejected once more here.

    The two rejections are also what makes the filter safe across joins: each
    ``filter()`` on the jobs of a unit opens a join of its own, so the job that
    satisfies the ``released`` condition of the caller need not be the job that
    satisfies the area condition here. Excluding the foreign jobs outright does
    not care which join matched.

    :param queryset: The unit queryset to restrict
    :param area: The area of the client, or ``None`` for the main app
    :return: The restricted queryset
    """
    if area is None:
        return queryset.exclude(jobs__area__isnull=False).distinct()
    return (
        queryset.filter(jobs__area=area)
        .exclude(jobs__area__isnull=True)
        .exclude(jobs__area__in=Area.objects.exclude(pk=area.pk))
        .distinct()
    )


def published_words(queryset: QuerySet[Word], area: Area | None) -> QuerySet[Word]:
    """
    Restrict a word queryset to what the API publishes for the given area.

    The area of a word is the area of the units it is linked to, see
    :func:`published_units` for why both branches exclude rather than filter.

    :param queryset: The word queryset to restrict
    :param area: The area of the client, or ``None`` for the main app
    :return: The restricted queryset
    """
    if area is None:
        return queryset.exclude(units__jobs__area__isnull=False).distinct()
    return (
        queryset.filter(units__jobs__area=area)
        .exclude(units__jobs__area__isnull=True)
        .exclude(units__jobs__area__in=Area.objects.exclude(pk=area.pk))
        .distinct()
    )
