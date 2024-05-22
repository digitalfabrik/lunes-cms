from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import Discipline, TrainingSet, Document


def filter_feedback_by_creator(feedback_queryset, user):
    """
    Exclude feedback entries that are not related to objects created by the user
    """

    # Collect content type ID of discipline/trainingset/document model
    discipline_type_id = ContentType.objects.get(model="discipline").id
    trainingset_type_id = ContentType.objects.get(model="trainingset").id
    document_type_id = ContentType.objects.get(model="document").id

    # Collect IDs disciplines/training sets/documents created by the user
    user_discipline_ids = [
        discipline.id
        for discipline in Discipline.objects.filter(created_by__in=user.groups.all())
    ]
    user_trainingset_ids = [
        trainingset.id
        for trainingset in TrainingSet.objects.filter(created_by__in=user.groups.all())
    ]
    user_document_ids = [
        document.id
        for document in Document.objects.filter(created_by__in=user.groups.all())
    ]

    # content_object field of feedback object cannot be used for direct query
    # Use content_type and object_id instead
    user_feedback_entries = feedback_queryset.filter(
        Q(content_type=discipline_type_id, object_id__in=user_discipline_ids)
        | (
            Q(content_type=trainingset_type_id, object_id__in=user_trainingset_ids)
            | Q(content_type=document_type_id, object_id__in=user_document_ids)
        )
    )

    return user_feedback_entries
