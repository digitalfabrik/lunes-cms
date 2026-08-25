"""
Tests for the Review model (word-level review assignments, #644).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from lunes_cms.cmsv2.models import Review, Word


@pytest.mark.django_db
def test_same_word_and_reviewer_violates_unique_constraint() -> None:
    """A word must not be assigned twice to the same reviewer."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    reviewer = get_user_model().objects.create_user(username="reviewer")
    Review.objects.create(word=word, reviewer=reviewer)

    with pytest.raises(IntegrityError):
        Review.objects.create(word=word, reviewer=reviewer)


@pytest.mark.django_db
def test_deleting_assigning_user_keeps_review_but_clears_assigned_by() -> None:
    """assigned_by uses SET_NULL, so the Review must survive the assigner's deletion."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    reviewer = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_user(username="admin")
    review = Review.objects.create(word=word, reviewer=reviewer, assigned_by=admin_user)

    admin_user.delete()
    review.refresh_from_db()

    assert review.assigned_by is None


@pytest.mark.django_db
def test_deleting_reviewer_deletes_review() -> None:
    """reviewer uses CASCADE, so the Review must be removed with the reviewer."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    reviewer = get_user_model().objects.create_user(username="reviewer")
    review = Review.objects.create(word=word, reviewer=reviewer)

    reviewer.delete()

    assert not Review.objects.filter(pk=review.pk).exists()


@pytest.mark.django_db
def test_progress_status_reflects_completed_at() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    reviewer = get_user_model().objects.create_user(username="reviewer")
    review = Review.objects.create(word=word, reviewer=reviewer)

    assert review.progress_status == "IN_REVIEW"

    review.completed_at = timezone.now()

    assert review.progress_status == "COMPLETED"
