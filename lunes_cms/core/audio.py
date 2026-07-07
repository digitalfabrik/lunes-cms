from __future__ import annotations

import json
import subprocess
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _


def validate_audio_upload(uploaded_file: UploadedFile) -> None:
    """Probe an uploaded audio file with ffmpeg before it is saved to storage."""
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp.flush()
        probe_ffmpeg(tmp.name)
    uploaded_file.seek(0)


def run_ffmpeg(*args: str) -> "subprocess.CompletedProcess[bytes]":
    """
    Run ffmpeg with the given arguments, raising ValidationError on failure.

    Returns the completed process so callers can read stderr.
    """
    try:
        return subprocess.run(["ffmpeg", *args], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise ValidationError({"audio": _("Invalid audio file")}) from e


def probe_ffmpeg(path: str) -> None:
    """Probe an audio file path with ffmpeg to check that it contains a valid audio stream."""
    run_ffmpeg("-v", "error", "-i", path, "-map", "0:a:0", "-f", "null", "-")


#: True-peak ceiling and loudness range used alongside the integrated
#: loudness target (EBU R128 defaults, they rarely need tuning)
_LOUDNORM_TRUE_PEAK = -1.5
_LOUDNORM_RANGE = 11.0

#: Fallbacks if the source's sample rate / bitrate can't be probed
_DEFAULT_SAMPLE_RATE = "24000"
_DEFAULT_BITRATE = "96k"


def _probe_audio_params(path: str) -> tuple[str, str]:
    """
    Read the sample rate and bitrate of an audio file via ffprobe.

    Used to re-encode at the source's own rate/bitrate; loudnorm otherwise
    forces 48 kHz output and re-picks the bitrate, needlessly inflating files.
    Falls back to defaults if probing fails.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=sample_rate,bit_rate",
                "-of",
                "default=noprint_wrappers=1",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return _DEFAULT_SAMPLE_RATE, _DEFAULT_BITRATE
    values = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    sample_rate = values.get("sample_rate") or _DEFAULT_SAMPLE_RATE
    bitrate = values.get("bit_rate")
    if not bitrate or bitrate == "N/A":
        bitrate = _DEFAULT_BITRATE
    return sample_rate, bitrate


def _parse_loudnorm_stats(stderr: bytes) -> dict[str, str]:
    """Extract the JSON loudness measurement ffmpeg's loudnorm prints to stderr."""
    text = stderr.decode("utf-8", "replace")
    start, end = text.rfind("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValidationError({"audio": _("Could not measure audio loudness")})
    result: dict[str, str] = json.loads(text[start : end + 1])
    return result


def normalize_loudness(audio_bytes: bytes, target_lufs: float) -> bytes:
    """
    Normalize mp3 audio to a target integrated loudness (EBU R128 loudnorm).

    Generated TTS clips come back at inconsistent levels — and word audio and
    sentence audio differ noticeably — so playback volume jumps between items.
    Re-encoding every clip to the same integrated loudness keeps them even.

    Uses two passes: the first measures the clip's actual loudness, the second
    applies a fixed (linear) gain to reach the target. Single-pass loudnorm
    normalizes dynamically and is unreliable on single words, which is exactly
    where the volume jumps are worst.
    """
    target = f"loudnorm=I={target_lufs}:TP={_LOUDNORM_TRUE_PEAK}:LRA={_LOUDNORM_RANGE}"
    with (
        tempfile.NamedTemporaryFile(suffix=".mp3") as src,
        tempfile.NamedTemporaryFile(suffix=".mp3") as dst,
    ):
        src.write(audio_bytes)
        src.flush()
        sample_rate, bitrate = _probe_audio_params(src.name)

        # Pass 1: measure loudness. "-f null -" discards the audio output; we
        # only want loudnorm's measurement, which it prints as JSON to stderr.
        measurement = run_ffmpeg(
            "-i",
            src.name,
            "-af",
            f"{target}:print_format=json",
            "-f",
            "null",
            "-",
        )
        measured = _parse_loudnorm_stats(measurement.stderr)

        # Pass 2: feed pass 1's measurements back so loudnorm applies a single
        # fixed gain to hit the target, preserving the source rate/bitrate.
        run_ffmpeg(
            "-y",
            "-i",
            src.name,
            "-af",
            f"{target}:linear=true"
            f":measured_I={measured['input_i']}"
            f":measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}"
            f":measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}",
            "-ar",
            sample_rate,
            "-b:a",
            bitrate,
            dst.name,
        )
        dst.seek(0)
        return dst.read()
