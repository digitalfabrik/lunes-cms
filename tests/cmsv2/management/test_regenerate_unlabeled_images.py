"""
Tests for the command regenerating AI images without the AI-disclosure label.
"""

from __future__ import annotations

import datetime
from collections.abc import Generator
from pathlib import Path
from unittest import mock

import pytest
from django.core.management import call_command
from pytest_django import Settings

from lunes_cms.cmsv2.management.commands import regenerate_unlabeled_images
from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus, ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from tests.cmsv2.images import c2pa_webp_bytes, store_image, webp_bytes

UTC = datetime.timezone.utc
AFTER = datetime.datetime(2026, 8, 20, tzinfo=UTC)
BEFORE = datetime.datetime(2026, 7, 1, tzinfo=UTC)


@pytest.fixture
def media_root(settings: Settings, tmp_path: Path) -> Path:
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def openai() -> Generator[mock.MagicMock, None, None]:
    with mock.patch.object(
        regenerate_unlabeled_images,
        "openai_image_bytes",
        return_value=c2pa_webp_bytes((8, 8)),
    ) as generate:
        yield generate


def _legacy_word(
    media_root: Path, word: str, when: datetime.datetime, data: bytes
) -> Word:
    """A word whose image was stored before its source was tracked."""
    instance = Word.objects.create(word=word, singular_article=1)
    Word.objects.filter(pk=instance.pk).update(
        image=store_image(media_root, when, data),
        image_check_status=CheckStatus.CONFIRMED,
        image_source=ImageSource.UNKNOWN,
    )
    instance.refresh_from_db()
    return instance


def _run(*args: str) -> None:
    call_command("regenerate_unlabeled_images", "--delay", "0", *args)


@pytest.mark.django_db
def test_records_the_source_of_legacy_images(
    media_root: Path, openai: mock.MagicMock
) -> None:
    labeled = _legacy_word(media_root, "Säge", AFTER, c2pa_webp_bytes())
    upload = _legacy_word(media_root, "Zange", AFTER, webp_bytes((800, 600)))
    old = _legacy_word(media_root, "Hammer", BEFORE, webp_bytes((1024, 1024)))

    _run()

    for word in (labeled, upload, old):
        word.refresh_from_db()
    assert labeled.image_source == ImageSource.AI_LABELED
    assert upload.image_source == ImageSource.UPLOADED
    # Too old to be regenerated, but recorded all the same.
    assert old.image_source == ImageSource.AI_UNLABELED
    openai.assert_not_called()


@pytest.mark.django_db
def test_regenerates_unlabeled_images_and_keeps_their_check_status(
    media_root: Path, openai: mock.MagicMock
) -> None:
    word = _legacy_word(media_root, "Hammer", AFTER, webp_bytes((1024, 1024)))
    old_file = media_root / str(word.image.name)

    _run()

    word.refresh_from_db()
    assert word.image_source == ImageSource.AI_RELABELED
    assert word.image_check_status == CheckStatus.CONFIRMED
    assert word.image.name != str(old_file.relative_to(media_root))
    assert str(word.image.name).endswith(".webp")
    assert word.image.read() == c2pa_webp_bytes((8, 8))
    assert not old_file.exists()
    assert "Hammer" in openai.call_args.args[0]


@pytest.mark.django_db
def test_regenerates_unit_images_with_their_unit(
    media_root: Path, openai: mock.MagicMock
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Werkzeug")
    unit.jobs.add(Job.objects.create(name="Tischler/-in"))
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    UnitWordRelation.objects.filter(pk=relation.pk).update(
        image=store_image(media_root, AFTER, webp_bytes((1024, 1024))),
        image_source=ImageSource.UNKNOWN,
    )

    _run()

    relation.refresh_from_db()
    assert relation.image_source == ImageSource.AI_RELABELED
    prompt = openai.call_args.args[0]
    assert "Werkzeug" in prompt
    assert "Tischler/-in" in prompt


@pytest.mark.django_db
def test_leaves_uploads_labeled_and_old_images_alone(
    media_root: Path, openai: mock.MagicMock
) -> None:
    _legacy_word(media_root, "Säge", AFTER, c2pa_webp_bytes())
    _legacy_word(media_root, "Zange", AFTER, webp_bytes((800, 600)))
    _legacy_word(media_root, "Hammer", BEFORE, webp_bytes((1024, 1024)))

    _run()

    openai.assert_not_called()


@pytest.mark.django_db
def test_since_moves_the_cutoff(media_root: Path, openai: mock.MagicMock) -> None:
    _legacy_word(media_root, "Hammer", BEFORE, webp_bytes((1024, 1024)))

    _run("--since", "2026-06-01")

    openai.assert_called_once()


@pytest.mark.django_db
def test_dry_run_changes_nothing(media_root: Path, openai: mock.MagicMock) -> None:
    word = _legacy_word(media_root, "Hammer", AFTER, webp_bytes((1024, 1024)))

    _run("--dry-run")

    word.refresh_from_db()
    assert word.image_source == ImageSource.UNKNOWN
    openai.assert_not_called()


@pytest.mark.django_db
def test_limit_caps_the_number_of_regenerated_images(
    media_root: Path, openai: mock.MagicMock
) -> None:
    _legacy_word(media_root, "Hammer", AFTER, webp_bytes((1024, 1024)))
    _legacy_word(media_root, "Säge", AFTER, webp_bytes((1024, 1024)))

    _run("--limit", "1")

    assert openai.call_count == 1
    assert Word.objects.filter(image_source=ImageSource.AI_UNLABELED).count() == 1


@pytest.mark.django_db
def test_a_failed_generation_keeps_the_old_image(
    media_root: Path, openai: mock.MagicMock
) -> None:
    word = _legacy_word(media_root, "Hammer", AFTER, webp_bytes((1024, 1024)))
    old_name = word.image.name
    openai.side_effect = ValueError("boom")

    _run()

    word.refresh_from_db()
    assert word.image.name == old_name
    assert word.image_source == ImageSource.AI_UNLABELED
