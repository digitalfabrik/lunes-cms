"""
Tests for telling from an image file where it came from.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from pytest_django import Settings

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import ImageSource
from lunes_cms.cmsv2.services.image_provenance import (
    classify_image,
    has_c2pa_manifest,
    image_created_at,
)
from tests.cmsv2.images import c2pa_webp_bytes, store_image, uuid1_at, webp_bytes

WHEN = datetime.datetime(2026, 8, 20, 12, 30, tzinfo=datetime.timezone.utc)


def test_c2pa_manifest_is_found_in_openai_webp(tmp_path: Path) -> None:
    path = tmp_path / "generated.webp"
    path.write_bytes(c2pa_webp_bytes((8, 8)))
    assert has_c2pa_manifest(str(path))


@pytest.mark.parametrize(
    "data", [webp_bytes(), b"", b"RIFF\x04\x00\x00\x00WEBP", b"\x89PNG\r\n\x1a\n"]
)
def test_c2pa_manifest_is_not_found_elsewhere(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "other.webp"
    path.write_bytes(data)
    assert not has_c2pa_manifest(str(path))


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (c2pa_webp_bytes(), ImageSource.AI_LABELED),
        (webp_bytes((1024, 1024)), ImageSource.AI_UNLABELED),
        (webp_bytes((800, 600)), ImageSource.UPLOADED),
    ],
)
@pytest.mark.django_db
def test_classify_image(
    settings: Settings, tmp_path: Path, data: bytes, expected: ImageSource
) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    word = Word(word="Hammer", image=store_image(tmp_path, WHEN, data))
    assert classify_image(word.image) == expected


@pytest.mark.django_db
def test_classify_image_returns_none_for_a_missing_file(
    settings: Settings, tmp_path: Path
) -> None:
    settings.MEDIA_ROOT = str(tmp_path)
    word = Word(word="Hammer", image="images/missing.webp")
    assert classify_image(word.image) is None


def test_image_created_at_reads_the_uuid1_timestamp() -> None:
    assert image_created_at(f"images/{uuid1_at(WHEN)}.webp") == WHEN


@pytest.mark.parametrize(
    "name",
    [
        "images/hammer.webp",
        # A version 4 UUID carries no time.
        "images/0b7f7a4e-6a5f-4c63-9d2b-5d1b0f3e2a61.webp",
        "images/",
    ],
)
def test_image_created_at_is_none_without_uuid1(name: str) -> None:
    assert image_created_at(name) is None
