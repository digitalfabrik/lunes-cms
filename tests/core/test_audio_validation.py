"""
Tests for the audio validation logic in Document.clean() and Word.clean().
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from lunes_cms.cms.models.document import Document
from lunes_cms.cmsv2.models.word import Word
from lunes_cms.core.audio import normalize_loudness

#: These tests invoke real ffmpeg/ffprobe, which aren't installed everywhere
#: (e.g. CI). Skip rather than fail when the binaries are missing.
requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe not installed",
)


class TestDocumentClean:
    def test_passes_when_no_audio(self) -> None:
        document = Document(word="Hammer", singular_article=1)
        document.clean()

    def test_skips_validation_for_committed_audio(self) -> None:
        document = Document(word="Hammer", singular_article=1)
        document.audio = "audio/existing.mp3"

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload"
        ) as mock_validate:
            document.clean()

        mock_validate.assert_not_called()

    def test_calls_validation_for_new_upload(self) -> None:
        document = Document(word="Hammer", singular_article=1)
        document.audio = ContentFile(b"fake-mp3", name="test.mp3")

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload"
        ) as mock_validate:
            document.clean()

        mock_validate.assert_called_once()

    def test_raises_for_invalid_audio(self) -> None:
        document = Document(word="Hammer", singular_article=1)
        document.audio = ContentFile(b"not-audio", name="test.mp3")

        with mock.patch(
            "lunes_cms.cms.models.document.validate_audio_upload",
            side_effect=ValidationError({"audio": "Invalid audio file"}),
        ):
            with pytest.raises(ValidationError):
                document.clean()


class TestWordClean:
    def test_passes_when_no_audio(self) -> None:
        word = Word(word="Hammer", singular_article=1)
        word.clean()

    def test_calls_validation_for_new_upload(self) -> None:
        word = Word(word="Hammer", singular_article=1)
        word.audio = ContentFile(b"fake-mp3", name="test.mp3")

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload"
        ) as mock_validate:
            word.clean()

        mock_validate.assert_called_once()

    def test_raises_for_invalid_audio(self) -> None:
        word = Word(word="Hammer", singular_article=1)
        word.audio = ContentFile(b"not-audio", name="test.mp3")

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload",
            side_effect=ValidationError({"audio": "Invalid audio file"}),
        ):
            with pytest.raises(ValidationError):
                word.clean()

    @pytest.mark.django_db
    def test_skips_validation_for_unchanged_audio(self) -> None:
        word = Word.objects.create(word="Hammer", singular_article=1)
        Word.objects.filter(pk=word.pk).update(audio="audio/hammer.mp3")
        word.refresh_from_db()

        with mock.patch(
            "lunes_cms.cmsv2.models.word.validate_audio_upload"
        ) as mock_validate:
            word.clean()

        mock_validate.assert_not_called()


def _make_mp3(
    tmp_path: Path,
    volume: str = "0.2",
    sample_rate: str = "24000",
    duration: str = "0.7",
) -> bytes:
    """Render a short, quiet mono mp3 with ffmpeg, mimicking a generated word clip."""
    path = tmp_path / "tone.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=300:duration={duration}",
            "-filter:a",
            f"volume={volume}",
            "-ar",
            sample_rate,
            "-ac",
            "1",
            "-b:a",
            "128k",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path.read_bytes()


def _measure_lufs(audio_bytes: bytes, tmp_path: Path) -> float:
    path = tmp_path / "measure.mp3"
    path.write_bytes(audio_bytes)
    result = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    stats = result.stderr[result.stderr.rfind("{") : result.stderr.rfind("}") + 1]
    return float(json.loads(stats)["input_i"])


@requires_ffmpeg
class TestNormalizeLoudness:
    def test_brings_quiet_clip_to_target_loudness(self, tmp_path: Path) -> None:
        raw = _make_mp3(tmp_path, volume="0.2")

        normalized = normalize_loudness(raw, -16.0)

        # Within 2 LU of the target — two-pass linear gain is accurate even on
        # the very short clips that single-pass loudnorm handles poorly.
        assert abs(_measure_lufs(normalized, tmp_path) - (-16.0)) < 2.0

    def test_preserves_source_sample_rate(self, tmp_path: Path) -> None:
        raw = _make_mp3(tmp_path, sample_rate="24000")

        normalized = normalize_loudness(raw, -16.0)

        path = tmp_path / "out.mp3"
        path.write_bytes(normalized)
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=sample_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        # loudnorm would otherwise force 48 kHz; we re-encode at the source rate.
        assert probe.stdout.strip() == "24000"

    def test_raises_validation_error_on_invalid_audio(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError):
            normalize_loudness(b"not-an-mp3", -16.0)
