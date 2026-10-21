"""
Mark generated audio as AI-generated in a machine-readable way (EU AI Act Art. 50).

The marking is the same XMP packet the images carry (IPTC ``DigitalSourceType``),
stored the way the XMP specification prescribes for MP3: in an ID3v2 ``PRIV``
frame owned by ``XMP``. ffmpeg keeps the frame when the file is re-encoded
later (``Word.convert_audio()``), so it is written once, right after
generation.
"""

import tempfile

from lunes_cms.core.audio import run_ffmpeg

from .xmp import build_xmp_packet

XMP_PACKET = build_xmp_packet("AI-generated audio")


def mark_as_ai_generated(audio_bytes: bytes) -> bytes:
    """
    Return the mp3 with the AI-generated marking added as an XMP ``PRIV`` frame.

    The audio stream is copied, not re-encoded.

    :param audio_bytes: mp3 bytes as produced by text-to-speech
    :return: the same audio with the marking added
    :raises ValidationError: if ffmpeg cannot process the audio
    """
    with (
        tempfile.NamedTemporaryFile(suffix=".mp3") as src,
        tempfile.NamedTemporaryFile(suffix=".mp3") as dst,
    ):
        src.write(audio_bytes)
        src.flush()
        run_ffmpeg(
            "-y",
            "-i",
            src.name,
            "-c",
            "copy",
            "-id3v2_version",
            "3",
            "-metadata",
            f"id3v2_priv.XMP={XMP_PACKET}",
            dst.name,
        )
        dst.seek(0)
        return dst.read()
