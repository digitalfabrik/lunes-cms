"""
Tests for :meth:`~lunes_cms.cmsv2.models.Word.ai_generated_images_for_api`, which
tells the API clients which images to disclose as AI-generated (issue #936).
"""

from __future__ import annotations

import pytest

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import CheckStatus, ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation

# Creating a word looks up the main app area as its default area.
pytestmark = pytest.mark.django_db


def _word(image_source: str, *relation_sources: str) -> Word:
    """
    An unsaved word with a confirmed default image of the given source and one
    public unit relation image per given relation source.
    """
    word = Word(
        word="Zirkel",
        image="images/word.webp",
        image_source=image_source,
        image_check_status=CheckStatus.CONFIRMED,
    )
    word.unit_word_relations_of_job = [  # type: ignore[attr-defined]
        UnitWordRelation(image=f"images/relation-{index}.webp", image_source=source)
        for index, source in enumerate(relation_sources)
    ]
    return word


@pytest.mark.parametrize(
    "source", [ImageSource.AI_UNLABELED, ImageSource.AI_LABELED, ImageSource.AI_MARKED]
)
def test_ai_generated_images_contain_every_ai_source(source: str) -> None:
    """Every AI image source counts as AI-generated, labeled or not."""
    word = _word(source)

    assert [image.name for image in word.ai_generated_images_for_api()] == [
        "images/word.webp"
    ]


@pytest.mark.parametrize("source", [ImageSource.UPLOADED, ImageSource.UNKNOWN])
def test_uploaded_and_unknown_images_are_not_ai_generated(source: str) -> None:
    """Uploads and images of unknown source are not disclosed as AI-generated."""
    assert not _word(source).ai_generated_images_for_api()


def test_ai_generated_images_are_the_ai_subset_of_the_images() -> None:
    """Only the AI images of the word and its relations are listed, in order."""
    word = _word(ImageSource.AI_LABELED, ImageSource.UPLOADED, ImageSource.AI_MARKED)

    assert [image.name for image in word.images_for_api()] == [
        "images/relation-0.webp",
        "images/relation-1.webp",
        "images/word.webp",
    ]
    assert [image.name for image in word.ai_generated_images_for_api()] == [
        "images/relation-1.webp",
        "images/word.webp",
    ]
