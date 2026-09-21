from __future__ import annotations

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from .areas import scope_jobs, scope_units, scope_words
from .models import Feedback, Job, Unit, Word


def filter_feedback_by_creator(
    feedback_queryset: QuerySet[Feedback], user: User
) -> QuerySet[Feedback]:
    """
    Exclude feedback entries that are not related to objects created by the user
    """

    job_type_id = ContentType.objects.get(app_label="cmsv2", model="job").id
    unit_type_id = ContentType.objects.get(app_label="cmsv2", model="unit").id
    word_type_id = ContentType.objects.get(app_label="cmsv2", model="word").id

    # Collect IDs of jobs/units/words created by the user's groups
    user_job_ids = Job.objects.filter(created_by__in=user.groups.all()).values_list(
        "id", flat=True
    )
    user_unit_ids = Unit.objects.filter(created_by__in=user.groups.all()).values_list(
        "id", flat=True
    )
    user_word_ids = Word.objects.filter(created_by__in=user.groups.all()).values_list(
        "id", flat=True
    )

    # content_object field of feedback object cannot be used for direct query
    # Use content_type and object_id instead
    return feedback_queryset.filter(
        Q(content_type=job_type_id, object_id__in=user_job_ids)
        | Q(content_type=unit_type_id, object_id__in=user_unit_ids)
        | Q(content_type=word_type_id, object_id__in=user_word_ids)
    )


def filter_feedback_by_area(
    feedback_queryset: QuerySet[Feedback], user: User
) -> QuerySet[Feedback]:
    """
    Restrict feedback entries to the ones about jobs, units or words of the
    areas the user administers, mirroring the scoping rules in
    :mod:`..areas`. A user who administers no area sees nothing, just as for
    the jobs, units and words themselves (#1016).
    """

    job_type_id = ContentType.objects.get(app_label="cmsv2", model="job").id
    unit_type_id = ContentType.objects.get(app_label="cmsv2", model="unit").id
    word_type_id = ContentType.objects.get(app_label="cmsv2", model="word").id

    user_job_ids = scope_jobs(Job.objects.all(), user).values_list("id", flat=True)
    user_unit_ids = scope_units(Unit.objects.all(), user).values_list("id", flat=True)
    user_word_ids = scope_words(Word.objects.all(), user).values_list("id", flat=True)

    # content_object field of feedback object cannot be used for direct query
    # Use content_type and object_id instead
    return feedback_queryset.filter(
        Q(content_type=job_type_id, object_id__in=user_job_ids)
        | Q(content_type=unit_type_id, object_id__in=user_unit_ids)
        | Q(content_type=word_type_id, object_id__in=user_word_ids)
    )


def filter_feedback_by_creator_and_area(
    feedback_queryset: QuerySet[Feedback], user: User
) -> QuerySet[Feedback]:
    """
    Restrict feedback entries to the ones about jobs, units or words that
    were both created by one of the user's groups AND belong to an area the
    user administers. Both conditions are combined with a logical AND, so a
    user who administers the right area but is not in the creating group (or
    vice versa) sees nothing for that entry.
    """
    return filter_feedback_by_area(
        filter_feedback_by_creator(feedback_queryset, user), user
    )
