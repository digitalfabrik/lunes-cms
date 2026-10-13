"""
Tests for the AI-generated marking of generated audio.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from pytest_django import Settings

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.services.audio_marking import mark_as_ai_generated
from lunes_cms.cmsv2.services.xmp import DIGITAL_SOURCE_TYPE_URI

_REAL_CONVERT_AUDIO = Word.convert_audio

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


def _make_mp3(tmp_path: Path) -> bytes:
    path = tmp_path / "source.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-b:a",
            "96k",
            str(path),
        ],
        check=True,
    )
    return path.read_bytes()


def _is_marked(path: str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", path],
        check=True,
        capture_output=True,
        text=True,
    )
    tags: dict[str, str] = json.loads(result.stdout).get("format", {}).get("tags", {})
    return DIGITAL_SOURCE_TYPE_URI in tags.get("id3v2_priv.XMP", "")


@requires_ffmpeg
class TestMarkAsAiGenerated:
    def test_adds_xmp_marking(self, tmp_path: Path) -> None:
        marked = tmp_path / "marked.mp3"
        marked.write_bytes(mark_as_ai_generated(_make_mp3(tmp_path)))

        assert _is_marked(str(marked))

    def test_xmp_packet_is_stored_in_priv_frame_owned_by_xmp(
        self, tmp_path: Path
    ) -> None:
        marked = mark_as_ai_generated(_make_mp3(tmp_path))

        assert marked[marked.index(b"PRIV") + 10 :].startswith(b"XMP\x00")

    def test_unmarked_audio_is_not_marked(self, tmp_path: Path) -> None:
        source = tmp_path / "source.mp3"
        source.write_bytes(_make_mp3(tmp_path))

        assert not _is_marked(str(source))

    @pytest.mark.django_db
    def test_marking_survives_word_convert_audio(
        self, tmp_path: Path, settings: Settings
    ) -> None:
        settings.MEDIA_ROOT = str(tmp_path)
        word = Word(word="Hammer")
        word.audio.save(
            "hammer.mp3",
            ContentFile(mark_as_ai_generated(_make_mp3(tmp_path))),
            save=False,
        )

        _REAL_CONVERT_AUDIO(word)

        assert _is_marked(word.audio.path)
