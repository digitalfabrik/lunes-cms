"""
Tests for assigning words to reviewers.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.utils import translation

from lunes_cms.cmsv2.models import Review, Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.reviews import assign_reviews, available_units_per_word


@pytest.fixture
def reviewer(db: None) -> User:
    return get_user_model().objects.create_user(username="reviewer")


@pytest.fixture
def assigner(db: None) -> User:
    return get_user_model().objects.create_superuser(
        username="admin", password="password"
    )


def _assign(unit_words: list[UnitWordRelation], reviewer: User, assigner: User) -> str:
    with translation.override("en"):
        return str(
            assign_reviews(
                UnitWordRelation.objects.filter(pk__in=[uw.pk for uw in unit_words]),
                reviewer=reviewer,
                assigner=assigner,
            )
        )


def test_available_units_per_word_separates_words_without_unit(db: None) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    word_without_unit = Word.objects.create(word="Zange", singular_article=2)
    unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit A"), word=word
    )

    words_with_unit, words_without_unit = available_units_per_word(
        Word.objects.all(), limit_units_to=Unit.objects.all()
    )

    assert words_with_unit == [word]
    assert words_with_unit[0].available_review_relations == [unit_word]
    assert words_without_unit == [word_without_unit]


def test_available_units_per_word_only_offers_the_given_units(db: None) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    allowed_unit = Unit.objects.create(title="Unit A")
    allowed_unit_word = UnitWordRelation.objects.create(unit=allowed_unit, word=word)
    UnitWordRelation.objects.create(unit=Unit.objects.create(title="Unit B"), word=word)

    words_with_unit, _ = available_units_per_word(
        Word.objects.all(), limit_units_to=Unit.objects.filter(pk=allowed_unit.pk)
    )

    assert words_with_unit[0].available_review_relations == [allowed_unit_word]


def test_available_units_per_word_treats_words_outside_the_given_units_as_without_unit(
    db: None,
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=Unit.objects.create(title="Unit A"), word=word)

    words_with_unit, words_without_unit = available_units_per_word(
        Word.objects.all(), limit_units_to=Unit.objects.none()
    )

    assert words_with_unit == []
    assert words_without_unit == [word]


def test_assign_reviews_creates_a_review_per_unit_word(
    reviewer: User, assigner: User
) -> None:
    unit = Unit.objects.create(title="Unit A")
    unit_words = [
        UnitWordRelation.objects.create(
            unit=unit, word=Word.objects.create(word=name, singular_article=1)
        )
        for name in ("Hammer", "Zange")
    ]

    message = _assign(unit_words, reviewer, assigner)

    reviews = Review.objects.filter(reviewer=reviewer)
    assert {review.unit_word for review in reviews} == set(unit_words)
    assert all(review.assigned_by == assigner for review in reviews)
    assert message == "Assigned 2 word(s) to reviewer (0 already assigned)."


def test_assign_reviews_counts_already_assigned_unit_words_as_skipped(
    reviewer: User, assigner: User
) -> None:
    unit = Unit.objects.create(title="Unit A")
    already_assigned, new = [
        UnitWordRelation.objects.create(
            unit=unit, word=Word.objects.create(word=name, singular_article=1)
        )
        for name in ("Hammer", "Zange")
    ]
    Review.objects.create(unit_word=already_assigned, reviewer=reviewer)

    message = _assign([already_assigned, new], reviewer, assigner)

    assert Review.objects.filter(reviewer=reviewer).count() == 2
    assert message == "Assigned 1 word(s) to reviewer (1 already assigned)."


def test_assign_reviews_twice_skips_everything_the_second_time(
    reviewer: User, assigner: User
) -> None:
    unit = Unit.objects.create(title="Unit A")
    unit_words = [
        UnitWordRelation.objects.create(
            unit=unit, word=Word.objects.create(word=name, singular_article=1)
        )
        for name in ("Hammer", "Zange")
    ]
    _assign(unit_words, reviewer, assigner)

    message = _assign(unit_words, reviewer, assigner)

    assert Review.objects.filter(reviewer=reviewer).count() == 2
    assert message == "Assigned 0 word(s) to reviewer (2 already assigned)."


def test_assign_reviews_ignores_reviews_of_other_reviewers(
    reviewer: User, assigner: User
) -> None:
    unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit A"),
        word=Word.objects.create(word="Hammer", singular_article=1),
    )
    other_reviewer = get_user_model().objects.create_user(username="other")
    Review.objects.create(unit_word=unit_word, reviewer=other_reviewer)

    message = _assign([unit_word], reviewer, assigner)

    assert Review.objects.filter(unit_word=unit_word, reviewer=reviewer).exists()
    assert message == "Assigned 1 word(s) to reviewer (0 already assigned)."
