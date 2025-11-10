from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import Job, Unit, Word


def filter_feedback_by_creator(feedback_queryset, user):
    """
    Exclude feedback entries that are not related to objects created by the user
    """

    job_type_id = ContentType.objects.get(model="job").id
    unit_type_id = ContentType.objects.get(model="unit").id
    word_type_id = ContentType.objects.get(model="word").id

    # Collect IDs disciplines/training sets/documents created by the user
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
    user_feedback_entries = feedback_queryset.filter(
        Q(content_type=job_type_id, object_id__in=user_job_ids)
        | Q(content_type=unit_type_id, object_id__in=user_unit_ids)
        | Q(content_type=word_type_id, object_id__in=user_word_ids)
    )

    return user_feedback_entries
