"""
Tell from an image file where it came from, for images stored before the
``image_source`` field existed.

Images generated since the AI-disclosure label was added (issue #936) are
stored byte-for-byte as OpenAI encoded them, so they still carry OpenAI's
C2PA manifest. Older generated images were saved under a ``.png`` name and
re-encoded to WebP, which stripped the manifest; they are recognised by the
1024x1024 size every OpenAI request in this code base has asked for. Anything
else is an upload.
"""

from __future__ import annotations

import datetime
import logging
import os
import struct
import uuid
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError

from ..models.static import ImageSource

if TYPE_CHECKING:
    from django.db.models.fields.files import ImageFieldFile

logger = logging.getLogger(__name__)

#: Size of every image this code base has requested from OpenAI.
GENERATED_IMAGE_SIZE = (1024, 1024)

#: RIFF chunk the C2PA specification embeds its manifest store in for WebP.
C2PA_WEBP_CHUNK = b"C2PA"

#: Start of the Gregorian calendar, the epoch of UUID version 1 timestamps.
_UUID_EPOCH = datetime.datetime(1582, 10, 15, tzinfo=datetime.timezone.utc)


def has_c2pa_manifest(path: str) -> bool:
    """
    Check whether a WebP file carries a C2PA manifest chunk.

    Only the RIFF chunk headers are read, never the image data.

    :param path: Path of the image file
    :return: True if the file is a WebP with a ``C2PA`` chunk
    """
    with open(path, "rb") as file:
        header = file.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
            return False
        while chunk_header := file.read(8):
            if len(chunk_header) < 8:
                return False
            fourcc = chunk_header[:4]
            (size,) = struct.unpack("<I", chunk_header[4:])
            if fourcc == C2PA_WEBP_CHUNK:
                return True
            # Chunks are padded to an even length.
            file.seek(size + (size & 1), os.SEEK_CUR)
    return False


def classify_image(image: ImageFieldFile) -> ImageSource | None:
    """
    Guess where a stored image came from by looking at its file.

    :param image: The image field of a Word or UnitWordRelation
    :return: The guessed source, or None if the file cannot be read
    """
    try:
        path = image.path
        if has_c2pa_manifest(path):
            return ImageSource.AI_LABELED
        with Image.open(path) as img:
            size = img.size
    except (OSError, UnidentifiedImageError) as e:
        logger.warning("Cannot read image %s: %s", image.name, e)
        return None
    if size == GENERATED_IMAGE_SIZE:
        return ImageSource.AI_UNLABELED
    return ImageSource.UPLOADED


def image_created_at(name: str) -> datetime.datetime | None:
    """
    Read the time an image was stored from its file name.

    ``upload_to`` names every image after a version 1 UUID, which encodes the
    time it was created. Converting to WebP keeps the name, so this is the time
    of the original upload or generation, unlike the file's modification time.

    :param name: The name of the image file
    :return: The creation time, or None if the name is not a version 1 UUID
    """
    stem = os.path.splitext(os.path.basename(name))[0]
    try:
        parsed = uuid.UUID(stem)
    except ValueError:
        return None
    if parsed.version != 1:
        return None
    # UUID timestamps count 100 ns intervals.
    return _UUID_EPOCH + datetime.timedelta(microseconds=parsed.time // 10)
