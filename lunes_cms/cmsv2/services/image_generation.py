"""
Background image generation for Word objects.

Mirrors ``audio_generation``: the DB is the queue, a Word with an empty
``image`` is "pending". A worker thread picks pending rows, calls the OpenAI
image API, saves the file. Idempotent — already-populated rows are filtered
out, so re-runs are free.

The OpenAI call is made *outside* any DB transaction. An in-process lock makes
the drain single-flight; it is separate from the audio drain's lock so image
and audio generation can run concurrently.
"""

import base64
import logging
import threading
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import connection
from django.db.models import Q
from openai import RateLimitError

from ..models import Word
from ..utils import get_openai_client, OpenAIConfigurationError

logger = logging.getLogger(__name__)

_drain_lock = threading.Lock()


def build_image_prompt(
    word_text: str,
    unit_title: str | None = None,
    additional_info: str | None = None,
) -> str:
    """
    Build the German image-generation prompt shared by the on-demand admin
    view and the background import drain.
    """
    prompt = f"Ein realistisches, professionelles Foto, das eindeutig zeigt: {word_text}."
    if unit_title:
        prompt += f" Thematischer Kontext: {unit_title}."
    prompt += (
        " Nur das zentrale Motiv ist zu sehen, vor einem neutralen weißen Hintergrund,"
        " ohne zusätzliche Objekte. Fotorealistisch, keine Illustration, kein Rendering."
    )
    if additional_info:
        prompt += f" Hinweise zur Bildgestaltung: {additional_info}."
    prompt += (
        " Das Bild enthält keinerlei Text, Buchstaben, Zahlen,"
        " Beschriftungen, Untertitel oder Logos."
    )
    return prompt


def openai_word_image_bytes(word: Word) -> bytes:
    """
    Generate PNG bytes for a single word via the OpenAI image API.
    """
    client = get_openai_client()
    response = client.images.generate(
        model=settings.OPENAI_IMAGE_MODEL,
        prompt=build_image_prompt(word.word),
        size="1024x1024",
        quality=settings.OPENAI_IMAGE_QUALITY,
        n=1,
    )
    return base64.b64decode(response.data[0].b64_json)


def _generate_for_word_image(word: Word) -> None:
    """
    Generate a missing image for a single Word and save it to the ImageField.

    ``Word.save()`` converts the uploaded image to WebP and the field defaults
    ``image_check_status`` to ``NOT_CHECKED``. The file name is the UUID the
    field's ``upload_to`` assigns — same as every other image in the system.
    """
    if not word.image:
        data = openai_word_image_bytes(word)
        word.image.save("image.png", ContentFile(data))
        logger.info("Generated image for word_id=%s (%s)", word.pk, word.word)


def _pending_filter(word_ids: list[int] | None = None) -> Q:
    pending = (Q(image="") | Q(image__isnull=True)) & ~Q(word="")
    if word_ids is not None:
        pending &= Q(pk__in=word_ids)
    return pending


def drain_pending_images(
    word_ids: list[int] | None = None, throttle_seconds: float = 1.0
) -> None:
    """
    Process Words that need an image, one at a time, until none remain.

    ``word_ids`` restricts the drain to those Word rows (the ones a CSV
    import just created). Without it the whole table is scanned.

    Single-flight within the process: if another thread already holds the
    drain lock this call returns immediately.

    Failures on a single row are logged and the loop continues — the row's
    image field stays empty so it'll be picked up on the next pass.
    """
    # Non-blocking single-flight guard; released in the finally below.
    if not _drain_lock.acquire(blocking=False):  # pylint: disable=consider-using-with
        return
    failed_pks: set[int] = set()
    try:
        pending = Word.objects.filter(_pending_filter(word_ids)).count()
        logger.info(
            "Image drain starting: %s word(s) pending — "
            "up to %s OpenAI image request(s)",
            pending,
            pending,
        )
        while True:
            word = (
                Word.objects.filter(_pending_filter(word_ids))
                .exclude(pk__in=failed_pks)
                .first()
            )
            if word is None:
                return
            try:
                _generate_for_word_image(word)
            except OpenAIConfigurationError:
                logger.warning("OpenAI not configured — image worker exiting")
                return
            except RateLimitError:
                # Org RPM limit hit. Back off and retry the same row — the
                # SDK already did its own short retries before raising.
                logger.warning("OpenAI rate limit — backing off 30s")
                time.sleep(30)
                continue
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Image generation failed for word_id=%s — leaving for retry",
                    word.pk,
                )
                # Don't re-pick this row in this pass; it'll be retried on the
                # next drain (import / app restart).
                failed_pks.add(word.pk)
                continue
            time.sleep(throttle_seconds)
    finally:
        _drain_lock.release()
        connection.close()
