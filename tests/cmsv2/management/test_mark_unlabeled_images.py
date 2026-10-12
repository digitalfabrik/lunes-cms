"""
Tests for the command marking AI images without the AI-disclosure label.
"""

from __future__ import annotations

import datetime
import io
from pathlib import Path
from unittest import mock

import pytest
from django.core.management import call_command
from PIL import Image

from lunes_cms.cmsv2.management.commands import mark_unlabeled_images as mark_command
from lunes_cms.cmsv2.models import Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus, ImageSource
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services.image_marking import is_marked, mark_image
from tests.cmsv2.images import c2pa_webp_bytes, store_image, webp_bytes

GENERATED_SIZE = (1024, 1024)
AFTER = datetime.datetime(2026, 8, 20, tzinfo=datetime.timezone.utc)
BEFORE = datetime.datetime(2025, 6, 1, tzinfo=datetime.timezone.utc)


def _word_with_unknown_source(
    media_root: Path,
    word: str,
    data: bytes,
    when: datetime.datetime = AFTER,
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


def _run_command(*args: str) -> str:
    out = io.StringIO()
    call_command("mark_unlabeled_images", *args, stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_records_the_source_of_legacy_images(media_root: Path) -> None:
    labeled = _word_with_unknown_source(media_root, "Säge", c2pa_webp_bytes())
    upload = _word_with_unknown_source(media_root, "Zange", webp_bytes((800, 600)))
    old = _word_with_unknown_source(
        media_root, "Hammer", webp_bytes(GENERATED_SIZE), BEFORE
    )

    _run_command()

    for word in (labeled, upload, old):
        word.refresh_from_db()
    assert labeled.image_source == ImageSource.AI_LABELED
    assert upload.image_source == ImageSource.UPLOADED
    assert old.image_source == ImageSource.AI_UNLABELED


@pytest.mark.django_db
def test_marks_unlabeled_images_and_keeps_their_check_status(
    media_root: Path,
) -> None:
    word = _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    old_name = str(word.image.name)

    _run_command()

    word.refresh_from_db()
    assert word.image_source == ImageSource.AI_MARKED
    assert word.image_check_status == CheckStatus.CONFIRMED
    path = media_root / str(word.image.name)
    assert is_marked(path)
    with Image.open(path) as marked:
        assert marked.size == GENERATED_SIZE
    assert word.image.name != old_name
    assert not (media_root / old_name).exists()


@pytest.mark.django_db
def test_marks_unit_images(media_root: Path) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Werkzeug")
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    name = store_image(media_root, AFTER, webp_bytes(GENERATED_SIZE))
    UnitWordRelation.objects.filter(pk=relation.pk).update(
        image=name, image_source=ImageSource.UNKNOWN
    )

    _run_command()

    relation.refresh_from_db()
    assert relation.image_source == ImageSource.AI_MARKED
    assert relation.image.name != name
    assert is_marked(media_root / str(relation.image.name))
    assert not (media_root / name).exists()


@pytest.mark.django_db
def test_marks_a_shared_file_once_and_is_idempotent(media_root: Path) -> None:
    first = _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    second = Word.objects.create(word="Säge", singular_article=1)
    Word.objects.filter(pk=second.pk).update(
        image=first.image.name, image_source=ImageSource.UNKNOWN
    )
    old_name = str(first.image.name)

    _run_command()
    first.refresh_from_db()
    second.refresh_from_db()
    once = (media_root / str(first.image.name)).read_bytes()
    _run_command()

    assert first.image.name == second.image.name != old_name
    assert (media_root / str(first.image.name)).read_bytes() == once
    assert not (media_root / old_name).exists()
    assert set(Word.objects.values_list("image_source", flat=True)) == {
        ImageSource.AI_MARKED
    }


@pytest.mark.django_db
def test_keeps_the_old_file_while_another_row_still_uses_it(
    media_root: Path,
) -> None:
    word = _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    other = Word.objects.create(word="Säge", singular_article=1)
    Word.objects.filter(pk=other.pk).update(
        image=word.image.name, image_source=ImageSource.UPLOADED
    )
    old_name = str(word.image.name)

    _run_command()

    other.refresh_from_db()
    assert other.image.name == old_name
    assert (media_root / old_name).exists()


@pytest.mark.django_db
def test_leaves_uploads_labeled_and_old_images_alone(media_root: Path) -> None:
    labeled = _word_with_unknown_source(media_root, "Säge", c2pa_webp_bytes())
    upload = _word_with_unknown_source(media_root, "Zange", webp_bytes((800, 600)))
    old = _word_with_unknown_source(
        media_root, "Hammer", webp_bytes(GENERATED_SIZE), BEFORE
    )
    contents = {
        word.pk: (media_root / str(word.image.name)).read_bytes()
        for word in (labeled, upload, old)
    }

    _run_command()

    for word in (labeled, upload, old):
        assert (media_root / str(word.image.name)).read_bytes() == contents[word.pk]


@pytest.mark.django_db
def test_since_includes_older_images(media_root: Path) -> None:
    word = _word_with_unknown_source(
        media_root, "Hammer", webp_bytes(GENERATED_SIZE), BEFORE
    )

    _run_command("--since", "2025-05-01")

    word.refresh_from_db()
    assert word.image_source == ImageSource.AI_MARKED
    assert is_marked(media_root / str(word.image.name))


@pytest.mark.django_db
def test_dry_run_changes_nothing(media_root: Path) -> None:
    word = _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    path = media_root / str(word.image.name)
    content = path.read_bytes()

    _run_command("--dry-run")

    word.refresh_from_db()
    assert word.image_source == ImageSource.UNKNOWN
    assert path.read_bytes() == content


@pytest.mark.django_db
def test_limit_caps_the_number_of_marked_images(media_root: Path) -> None:
    _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    _word_with_unknown_source(media_root, "Säge", webp_bytes(GENERATED_SIZE))

    _run_command("--limit", "1")

    assert Word.objects.filter(image_source=ImageSource.AI_MARKED).count() == 1
    assert Word.objects.filter(image_source=ImageSource.AI_UNLABELED).count() == 1


@pytest.mark.django_db
def test_a_failing_image_does_not_stop_the_others(media_root: Path) -> None:
    first = _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    second = _word_with_unknown_source(media_root, "Säge", webp_bytes(GENERATED_SIZE))
    real_mark_image = mark_command.mark_image

    def fail_for_first(source_path: str, target_path: str) -> bool:
        if source_path == first.image.path:
            raise ValueError("boom")
        return real_mark_image(source_path, target_path)

    with mock.patch.object(mark_command, "mark_image", side_effect=fail_for_first):
        _run_command()

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.image_source == ImageSource.AI_UNLABELED
    assert (media_root / str(first.image.name)).exists()
    assert second.image_source == ImageSource.AI_MARKED


@pytest.mark.django_db
def test_summary_reports_already_marked_images(media_root: Path) -> None:
    _word_with_unknown_source(media_root, "Hammer", webp_bytes(GENERATED_SIZE))
    already = _word_with_unknown_source(media_root, "Säge", webp_bytes(GENERATED_SIZE))
    old_path = Path(already.image.path)

    mark_image(str(old_path), str(old_path.with_name("tmp.webp")))
    old_path.with_name("tmp.webp").replace(old_path)

    output = _run_command()

    assert "Marked 1 of 2 image(s), 1 already marked." in output
