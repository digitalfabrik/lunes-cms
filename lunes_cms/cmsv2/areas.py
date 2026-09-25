"""
Area scoping and the invariants that keep the content of an area separate.

Jobs, units and words each store their area in a foreign key of their own, so
content belongs to an area from the moment it is created, whether or not it is
linked to anything yet, see #1061. The main app catalog is not the absence of
an area but the one area with ``is_main_app=True``, see #1016. Only units and
words that could not be assigned an area automatically have none, and those
are left to the superusers to assign. The relations have to stay inside an
area: a unit can only be assigned to jobs of its own area and a word can only
be used in units of its own area. This module is the single place that knows
these rules, so admins, views and the API can share them.

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
    from django.utils.functional import _StrOrPromise

    # Imported for the annotations only: importing the models package for real
    # would run into the import of this module in ``UnitWordRelation.clean()``.
    from .models import AlternativeWord, Job, Unit, UnitWordRelation, Word

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


def accessible_areas(user: "User") -> "QuerySet[Area]":
    """
    :param user: The user in question
    :return: The queryset of areas that the user may access
    """
    if not user.is_authenticated:
        return Area.objects.none()
    if getattr(user, "is_superuser", False):
        return Area.objects.all()
    return administered_areas(user)


def is_area_admin(user: "User") -> bool:
    """
    Whether the given user administers at least one area of a part organization.

    :param user: The user in question
    :return: Whether the user is the administrator of any such area
    """
    return administered_areas(user).exists()


def default_area(user: "User") -> Area:
    """
    The area new content of the given user is put into, see #1061.

    An administrator of a single area creates content in that area. A
    superuser, an administrator of several areas and anybody else create
    content of the main app catalog by default — unless they administer
    several areas but not the main app, in which case it is the first of
    their own areas, since they cannot pick any other.

    :param user: The user who creates the content
    :return: The default area of the content
    """
    main_app_area = Area.objects.get(is_main_app=True)
    if getattr(user, "is_superuser", False):
        return main_app_area
    areas = list(administered_areas(user))
    if len(areas) == 1 or (areas and main_app_area not in areas):
        return areas[0]
    return main_app_area


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

    The same rules as :func:`scope_jobs` apply. A unit without an area is only
    visible to superusers, who have to assign it to one.

    :param queryset: The unit queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    return queryset.filter(area__in=administered_areas(user))


def scope_words(queryset: "QuerySet[Word]", user: "User") -> "QuerySet[Word]":
    """
    Restrict a word queryset to what the given user may see.

    The same rules as :func:`scope_jobs` apply. A word without an area is only
    visible to superusers, who have to assign it to one.

    :param queryset: The word queryset to restrict
    :param user: The user the queryset is restricted to
    :return: The restricted queryset
    """
    if getattr(user, "is_superuser", False):
        return queryset
    return queryset.filter(area__in=administered_areas(user))


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
    return queryset.filter(unit__area__in=administered_areas(user))


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
    return queryset.filter(word__area__in=administered_areas(user))


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


def area_conflict_message(
    word: "Word", existing_area: Area | None, new_area: Area | None
) -> "_StrOrPromise":
    """
    The message shown when a word cannot be linked to a unit of another area.

    :param word: The word that cannot be linked
    :param existing_area: The area the word already belongs to
    :param new_area: The area the conflicting unit belongs to
    :return: The translated message
    """
    return _(
        'The word "%(word)s" already belongs to area "%(existing_area)s" and '
        'cannot also be used in area "%(new_area)s".'
    ) % {
        "word": word,
        "existing_area": existing_area or _("no area"),
        "new_area": new_area or _("no area"),
    }


def validate_unit_jobs(jobs: "Iterable[Job]", area: Area | None) -> None:
    """
    Check that the given jobs may be assigned to a unit of the given area.

    A unit can only be assigned to jobs of its own area. A unit of a partner
    area must not be assigned to more than one job at all, only the units of
    the main app catalog are shared between its jobs.

    :param jobs: The jobs the unit is about to be assigned to
    :param area: The area the unit is about to belong to
    :raises ~django.core.exceptions.ValidationError: If the assignment would
                                                     mix areas
    """
    jobs = list(jobs)
    for job in jobs:
        if job.area_id != (area.pk if area else None):
            raise ValidationError(
                _(
                    'The job "%(job)s" belongs to area "%(job_area)s", but this '
                    'unit belongs to area "%(unit_area)s".'
                )
                % {
                    "job": job,
                    "job_area": job.area,
                    "unit_area": area or _("no area"),
                }
            )
    if area is not None and not area.is_main_app and len(jobs) > 1:
        raise ValidationError(
            _(
                "A unit of a job that belongs to an area must not be assigned "
                "to any other job."
            )
        )


def validate_unit_area(unit: "Unit", area: Area | None) -> None:
    """
    Check that a unit may be moved into the given area.

    The words of a unit move along with it (see :func:`move_unit_to_area`),
    so a unit whose words are used in other units as well cannot be moved.
    Untangling that content is a manual decision and is left to the content
    managers. Whether the jobs of the unit fit the new area is checked by
    :func:`validate_unit_jobs`.

    :param unit: The unit that is about to be saved
    :param area: The area the unit is about to be moved into
    :raises ~django.core.exceptions.ValidationError: If the unit shares words
    """
    if not unit.pk:
        return
    for word in unit.words.prefetch_related("units"):
        if any(other.pk != unit.pk for other in word.units.all()):
            raise ValidationError(
                _(
                    'The word "%(word)s" is also used in other units, so this '
                    'unit cannot be moved into area "%(area)s".'
                )
                % {"word": word, "area": area or _("no area")}
            )


def validate_word_area(word: "Word", area: Area | None) -> None:
    """
    Check that a word may be moved into the given area.

    A word can only be used in units of its own area, so a word that is
    already used in units cannot be moved on its own — its units have to be
    moved instead, which takes the word along (see :func:`move_unit_to_area`).

    :param word: The word that is about to be saved
    :param area: The area the word is about to be moved into
    :raises ~django.core.exceptions.ValidationError: If the word is used in a
                                                     unit of another area
    """
    if not word.pk:
        return
    for unit in word.units.select_related("area"):
        if unit.area_id != (area.pk if area else None):
            raise ValidationError(
                _(
                    'The word is used in the unit "%(unit)s" of area '
                    '"%(unit_area)s" and therefore has to belong to that area.'
                )
                % {"unit": unit, "unit_area": unit.area or _("no area")}
            )


def validate_job_area(job: "Job", area: Area | None) -> None:
    """
    Check that a job may be moved into the given area.

    The units and words of a job move along with it (see
    :func:`move_job_to_area`), so a job whose units are shared with other
    jobs, or whose words are used outside of those units, cannot be moved.
    Untangling that content is a manual decision and is left to the content
    managers.

    :param job: The job that is about to be saved
    :param area: The area the job is about to be moved into
    :raises ~django.core.exceptions.ValidationError: If the job shares content
    """
    if area is None or not job.pk:
        return
    # words__units__jobs is prefetched so the "used elsewhere" check below
    # reads from cache instead of running a query per word.
    for unit in job.units.prefetch_related("jobs", "words__units__jobs"):
        other_jobs = [other for other in unit.jobs.all() if other.pk != job.pk]
        if other_jobs:
            raise ValidationError(
                _(
                    'The unit "%(unit)s" is also assigned to %(jobs)s, so this '
                    'job cannot be moved into area "%(area)s".'
                )
                % {
                    "unit": unit,
                    "jobs": ", ".join(str(other) for other in other_jobs),
                    "area": area,
                }
            )
        for word in unit.words.all():
            used_elsewhere = any(
                job not in w_unit.jobs.all() for w_unit in word.units.all()
            )
            if used_elsewhere:
                raise ValidationError(
                    _(
                        'The word "%(word)s" is also used outside of this job, '
                        'so this job cannot be moved into area "%(area)s".'
                    )
                    % {"word": word, "area": area}
                )


def validate_relation_area(unit: "Unit", word: "Word") -> None:
    """
    Check that a word may be linked to a unit.

    A word can only be used in units of its own area.

    :param unit: The unit the word is about to be linked to
    :param word: The word that is about to be linked
    :raises ~django.core.exceptions.ValidationError: If the link would mix areas
    """
    if unit.area_id != word.area_id:
        raise ValidationError(area_conflict_message(word, word.area, unit.area))


def move_unit_to_area(unit: "Unit") -> None:
    """
    Move the words of a unit into the area the unit was moved into.

    Call :func:`validate_unit_area` before moving the unit, so no word that
    is also used in other units is moved along.

    :param unit: The unit whose area was changed
    """
    # pylint: disable=import-outside-toplevel
    from .models import Word

    Word.objects.filter(units=unit).exclude(area=unit.area).update(area=unit.area)


def move_job_to_area(job: "Job") -> None:
    """
    Move the units and words of a job into the area the job was moved into.

    Call :func:`validate_job_area` before moving the job, so no unit or word
    that is also used outside of the job is moved along.

    :param job: The job whose area was changed
    """
    # pylint: disable=import-outside-toplevel
    from .models import Unit, Word

    Unit.objects.filter(jobs=job).exclude(area=job.area).update(area=job.area)
    Word.objects.filter(units__jobs=job).exclude(area=job.area).update(area=job.area)


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
