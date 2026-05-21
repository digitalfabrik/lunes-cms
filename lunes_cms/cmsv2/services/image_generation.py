"""
Background image generation for Word objects.

Mirrors ``audio_generation``: the DB is the queue, a Word with an empty
``image`` is "pending". A worker thread picks pending rows, calls the OpenAI
image API, saves the file. Idempotent — already-populated rows are filtered
out, so re-runs are free.

The drain is scoped to the word IDs just created by a CSV import (passed via
``word_ids``); it never touches words created elsewhere.

The OpenAI call is made *outside* any DB transaction. An in-process lock makes
the drain single-flight; it is separate from the audio drain's lock so image
and audio generation can run concurrently.

Triggered from ``import_csv_view`` after a successful CSV import. If a worker
dies mid-batch the remaining rows stay pending and are picked up on the next
import.
"""

import base64
import logging
import os
import threading
import time

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import connection
from django.db.models import Q
from openai import RateLimitError

from ..models import Word
from ..utils import get_openai_client, make_safe_filename, OpenAIConfigurationError

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
    prompt = """Du bist Content-Manager für eine Vokabel-Lern-App namens "Lunes". Die App richtet sich an Zugewanderte, die in Deutschland eine Ausbildung machen oder bereits beruflich tätig sind. Sie lernen Deutsch als Fremdsprache und benötigen spezifischen Fachwortschatz, der in regulären Sprachkursen nicht vermittelt wird.

        Die App zeigt Fachbegriffe aus dem Berufsfeld in Form von Bildern. Alle Vokabeln werden einsprachig (nur auf Deutsch) vermittelt – durch realistische Fotos, die das Wort eindeutig visuell darstellen.

        Für die Bildsprache gelten folgende Vorgaben:
        - Es sollen realistische Fotos sein (keine Illustrationen, keine Renderings).
        - Das Bildmotiv muss eindeutig dem jeweiligen Fachbegriff zuzuordnen sein.
        - Es soll nur der relevante Gegenstand oder die relevante Handlung zu sehen sein.
        - Keine zusätzlichen Objekte, kein Text, neutraler Hintergrund (z.B. weiß oder freigestellt).
    """
    if unit_title:
        prompt += f"Der Begriff gehört zum Lernmodul: {unit_title}"
    prompt += f'Erstelle ein passendes realistisches Foto zur Vokabel: "{word_text}"'
    if additional_info:
        prompt += f"Zusätzliche Hinweise zur Bildgestaltung: {additional_info}"
    prompt += "Ziel ist es, dass die Vokabel durch das Bild eindeutig verstanden werden kann – auch ohne Text oder Erklärung."
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


def _rename_image_to_word(word: Word) -> None:
    """
    Rename the stored image file to a deterministic, word-derived name.

    ``upload_to`` (``convert_umlaute_images``) names every uploaded image with
    a random UUID. Generated images get a "<word>.webp" name instead — mirrors
    how ``Word.convert_audio()`` names audio files. A pk suffix breaks ties if
    another word already owns that name.
    """
    old_name = word.image.name
    storage = word.image.storage
    directory = os.path.dirname(old_name)
    extension = os.path.splitext(old_name)[1]
    safe_stem = make_safe_filename(word.word) or "image"

    new_name = os.path.join(directory, f"{safe_stem}{extension}")
    if new_name == old_name:
        return
    if storage.exists(new_name):
        new_name = os.path.join(directory, f"{safe_stem}_{word.pk}{extension}")
        if storage.exists(new_name):
            storage.delete(new_name)

    with storage.open(old_name) as source:
        storage.save(new_name, source)
    storage.delete(old_name)
    word.image.name = new_name
    word.save(update_fields=["image"])


def _generate_for_word_image(word: Word) -> None:
    """
    Generate a missing image for a single Word and save it to the ImageField.

    ``Word.save()`` converts the uploaded image to WebP and the field defaults
    ``image_check_status`` to ``NOT_CHECKED``; afterwards the file is renamed
    to a word-derived name.
    """
    if not word.image:
        data = openai_word_image_bytes(word)
        word.image.save(
            f"{make_safe_filename(word.word)}.png",
            ContentFile(data),
        )
        _rename_image_to_word(word)
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
