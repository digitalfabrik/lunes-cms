"""
Tests for the ``backfill_alternative_words_from_v1`` migration, which restores
the alternative words entered in v1.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest
from django.apps import apps

from lunes_cms.cms.models import AlternativeWord as V1AlternativeWord, Document
from lunes_cms.cmsv2 import migrations as cmsv2_migrations
from lunes_cms.cmsv2.models import AlternativeWord, Word

(MIGRATION_PATH,) = Path(cmsv2_migrations.__file__).parent.glob(
    "*_backfill_alternative_words_from_v1.py"
)
migration = import_module(f"{cmsv2_migrations.__name__}.{MIGRATION_PATH.stem}")

pytestmark = pytest.mark.django_db


def backfill() -> None:
    """Run the migration's backfill against the current models."""
    migration.backfill_alternative_words(apps, None)


def v1_document(word: str = "Brötchen") -> Document:
    """A v1 document to hang alternative words off."""
    return Document.objects.create(word=word, singular_article=3)


def v1_alternative_word(
    document: Document, alt_word: str = "Semmel", **fields: int | str
) -> V1AlternativeWord:
    """An alternative word entered in v1, waiting to be restored."""
    return V1AlternativeWord.objects.create(
        document=document, alt_word=alt_word, singular_article=2, **fields
    )


def v2_word(document: Document | None = None) -> Word:
    """A word in the current CMS, migrated from ``document`` if one is given."""
    return Word.objects.create(
        word="Brötchen",
        singular_article=3,
        v1_id=document.id if document is not None else None,
    )


def test_alternative_words_of_a_migrated_word_are_restored() -> None:
    """The alternative words of a v1 document reappear on its v2 word."""
    document = v1_document()
    v1_alternative_word(
        document, grammatical_gender=2, plural="Semmeln", plural_article=1
    )
    word = v2_word(document)

    backfill()

    restored = word.alternative_words.get()
    assert restored.alt_word == "Semmel"
    assert restored.singular_article == 2
    assert restored.grammatical_gender == 2
    assert restored.plural == "Semmeln"
    assert restored.plural_article == 1


def test_all_alternative_words_of_a_word_are_restored() -> None:
    """A word with several synonyms in v1 gets all of them back."""
    document = v1_document()
    for alt_word in ("Semmel", "Weck", "Schrippe"):
        v1_alternative_word(document, alt_word)
    word = v2_word(document)

    backfill()

    assert sorted(word.alternative_words.values_list("alt_word", flat=True)) == [
        "Schrippe",
        "Semmel",
        "Weck",
    ]


def test_words_created_in_v2_are_left_alone() -> None:
    """A word without a v1_id has nothing to restore."""
    v1_alternative_word(v1_document())
    word = v2_word()

    backfill()

    assert not word.alternative_words.exists()


def test_words_with_existing_alternative_words_are_skipped() -> None:
    """
    Alternative words entered by hand since the v2 rollout are neither
    duplicated nor shadowed by the ones coming from v1.
    """
    document = v1_document()
    v1_alternative_word(document)
    word = v2_word(document)
    AlternativeWord.objects.create(word=word, alt_word="Weck", singular_article=2)

    backfill()

    assert list(word.alternative_words.values_list("alt_word", flat=True)) == ["Weck"]


def test_running_the_backfill_twice_restores_each_word_once() -> None:
    """The backfill is idempotent, so a re-run creates no duplicates."""
    document = v1_document()
    v1_alternative_word(document)
    word = v2_word(document)

    backfill()
    backfill()

    assert word.alternative_words.count() == 1


def test_alternative_words_of_other_documents_are_not_mixed_in() -> None:
    """Each word only gets the alternative words of its own v1 document."""
    brötchen = v1_document()
    v1_alternative_word(brötchen)
    v1_alternative_word(v1_document(word="Hammer"), alt_word="Fäustel")
    word = v2_word(brötchen)

    backfill()

    assert list(word.alternative_words.values_list("alt_word", flat=True)) == ["Semmel"]


def test_a_v1_document_without_a_v2_word_is_ignored() -> None:
    """Orphaned v1 documents do not blow the backfill up."""
    v1_alternative_word(v1_document(), alt_word="Nur-in-v1")

    backfill()

    assert not AlternativeWord.objects.filter(alt_word="Nur-in-v1").exists()
