from collections import defaultdict
from typing import TypedDict, List

from django.db.models import Count
from django.db.models.functions import Lower

from lunes_cms.cms.models import Document


class DuplicateVocabulary(TypedDict):
    """
    Dictionary type representing a duplicate vocabulary group
    """

    word: str
    word_type: str
    documents: List[Document]


class DuplicateVocabularyDocument(TypedDict):
    """
    Dictionary type representing a document with a duplicate vocabulary group
    """

    id: str
    word: str
    training_sets: List[str]


def map_to_duplicate_vocabulary_documents(documents) -> [DuplicateVocabularyDocument]:
    """
    Maps the result of the get duplicate vocabularies query to DuplicateVocabularyDocument
    """
    mapped = []
    for document in documents:
        training_sets = []
        for training_set in document.get("_prefetched_objects_cache").get(
            "training_sets", None
        ):
            training_sets.append(training_set.title)
        mapped.append(
            {"id": document.id, "word": document.word, "training_sets": training_sets}
        )
    return mapped


def get_duplicate_vocabularies() -> List[DuplicateVocabulary]:
    """
    Retrieves duplicate vocabularies from the database
    """
    duplicate_groups = (
        Document.objects.annotate(lower_word=Lower("word"))
        .values("lower_word", "word_type")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )
    duplicate_vocabularies = Document.objects.prefetch_related("training_sets").filter(
        id__in=Document.objects.annotate(lower_word=Lower("word"))
        .filter(
            lower_word__in=[group["lower_word"] for group in duplicate_groups],
            word_type__in=[group["word_type"] for group in duplicate_groups],
        )
        .values_list("id", flat=True)
    )

    grouped_duplicate_vocabularies = defaultdict(list)
    for v in duplicate_vocabularies:
        grouped_duplicate_vocabularies[(v.word.lower(), v.word_type)].append(v)

    result = []
    for _, value in grouped_duplicate_vocabularies.items():
        result.append(
            {
                "word": value[0].word,
                "word_type": value[0].word_type,
                "documents": map_to_duplicate_vocabulary_documents(value),
            }
        )
    return result
