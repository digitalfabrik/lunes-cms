"""
Tests for the image shown in the review detail of ReviewAdmin (#1079).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from lunes_cms.cmsv2.admins.review_admin import ReviewAdmin
from lunes_cms.cmsv2.models import Review, Unit, UnitWordRelation, Word


@pytest.mark.django_db
def test_review_image_renders_image_tag(media_root: Path) -> None:
    """The review detail shows the image itself, not its path."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Unit A")
    unit_word = UnitWordRelation.objects.create(unit=unit, word=word)
    unit_word.image.save("hammer.png", ContentFile(b"png"), save=False)
    reviewer = get_user_model().objects.create_user(username="reviewer")
    review = Review.objects.create(unit_word=unit_word, reviewer=reviewer)

    html = ReviewAdmin(Review, admin.site).review_image(review)

    assert html.startswith("<img ")
    assert f'src="{settings.MEDIA_URL}{unit_word.image.name}"' in html
    assert 'class="hidden"' not in html
