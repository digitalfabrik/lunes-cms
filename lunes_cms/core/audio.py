import subprocess
import tempfile

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_audio_upload(uploaded_file):
    """Probe an uploaded audio file with ffmpeg before it is saved to storage."""
    with tempfile.NamedTemporaryFile(suffix=".tmp") as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp.flush()
        probe_ffmpeg(tmp.name)
    uploaded_file.seek(0)


def run_ffmpeg(*args):
    """Run ffmpeg with the given arguments, raising ValidationError on failure."""
    try:
        subprocess.run(["ffmpeg", *args], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise ValidationError({"audio": _("Invalid audio file")}) from e


def probe_ffmpeg(path):
    """Probe an audio file path with ffmpeg to check it contains a valid audio stream."""
    run_ffmpeg("-v", "error", "-i", path, "-map", "0:a:0", "-f", "null", "-")
