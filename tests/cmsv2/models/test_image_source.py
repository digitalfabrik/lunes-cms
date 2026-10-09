"""
Tests for how Word and UnitWordRelation record where their image came from.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from pytest_django import Settings

from lunes_cms.cmsv2.models import Unit, Word
from lunes_cms.cmsv2.models.static import ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from tests.cmsv2.images import webp_bytes


@pytest.fixture(autouse=True)
def _media_root(settings: Settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.mark.django_db
def test_a_word_without_image_has_no_source() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    assert word.image_source == ImageSource.UNKNOWN


@pytest.mark.django_db
def test_a_new_image_is_an_upload_unless_stated_otherwise() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    word.image.save("hammer.webp", ContentFile(webp_bytes()))
    word.refresh_from_db()
    assert word.image_source == ImageSource.UPLOADED


@pytest.mark.django_db
def test_a_generated_image_keeps_its_stated_source() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    word.image.save("hammer.webp", ContentFile(webp_bytes()), save=False)
    word.save(image_source=ImageSource.AI_LABELED)
    word.refresh_from_db()
    assert word.image_source == ImageSource.AI_LABELED

    # Saving the word again must not turn the image into an upload.
    word.word = "Vorschlaghammer"
    word.save()
    word.refresh_from_db()
    assert word.image_source == ImageSource.AI_LABELED

    # Replacing it by hand does.
    word.image.save("upload.webp", ContentFile(webp_bytes()))
    word.refresh_from_db()
    assert word.image_source == ImageSource.UPLOADED


@pytest.mark.django_db
def test_removing_the_image_clears_its_source() -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    word.image.save("hammer.webp", ContentFile(webp_bytes()), save=False)
    word.save(image_source=ImageSource.AI_LABELED)
    word.image = None
    word.save()
    word.refresh_from_db()
    assert word.image_source == ImageSource.UNKNOWN


@pytest.mark.django_db
def test_unit_word_relation_records_its_image_source() -> None:
    relation = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Werkzeug"),
        word=Word.objects.create(word="Hammer", singular_article=1),
    )
    relation.image.save("hammer.webp", ContentFile(webp_bytes()))
    relation.refresh_from_db()
    assert relation.image_source == ImageSource.UPLOADED

    relation.image.save("generated.webp", ContentFile(webp_bytes()), save=False)
    relation.save(image_source=ImageSource.AI_LABELED)
    relation.refresh_from_db()
    assert relation.image_source == ImageSource.AI_LABELED
