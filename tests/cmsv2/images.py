"""
Image files that look like the ones the CMS stores, for provenance and marking tests.
"""

from __future__ import annotations

import datetime
import io
import secrets
import struct
import uuid
from pathlib import Path

from PIL import Image

_UUID_EPOCH = datetime.datetime(1582, 10, 15, tzinfo=datetime.timezone.utc)


def webp_bytes(size: tuple[int, int] = (4, 4)) -> bytes:
    """A plain WebP, like an editor upload after conversion."""
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="WEBP")
    return buf.getvalue()


def c2pa_webp_bytes(size: tuple[int, int] = (1024, 1024)) -> bytes:
    """A WebP with a C2PA chunk appended, like OpenAI's output."""
    data = webp_bytes(size)
    manifest = b"jumbfc2pa"
    chunk = b"C2PA" + struct.pack("<I", len(manifest)) + manifest + b"\0"
    body = data[8:] + chunk
    return b"RIFF" + struct.pack("<I", len(body)) + body


def uuid1_at(when: datetime.datetime) -> uuid.UUID:
    """
    A version 1 UUID carrying the timestamp ``when``, with a random node so
    two images stored at the same time get different names.
    """
    ticks = int((when - _UUID_EPOCH).total_seconds() * 10**7)
    return uuid.UUID(
        fields=(
            ticks & 0xFFFFFFFF,
            (ticks >> 32) & 0xFFFF,
            ((ticks >> 48) & 0x0FFF) | 0x1000,
            0x80,
            0,
            secrets.randbits(48),
        )
    )


def store_image(media_root: Path, when: datetime.datetime, data: bytes) -> str:
    """
    Write ``data`` where ``upload_to`` would have put an image stored at
    ``when``, and return its name relative to the media root.
    """
    name = f"images/{uuid1_at(when)}.webp"
    path = media_root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return name
