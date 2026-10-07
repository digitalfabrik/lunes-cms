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

from __future__ import annotations

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
from ..models.static import ImageSource
from ..utils import get_openai_client, OpenAIConfigurationError
from .ai_label import LABEL_PATH, LABEL_WIDTH_RATIO

logger = logging.getLogger(__name__)

_drain_lock = threading.Lock()

#: Format we ask OpenAI to encode generated images in. Not configurable: WebP
#: is what the CMS serves, so the stored file is byte-for-byte the one OpenAI
#: produced and its C2PA manifest and watermark survive (EU AI Act Art. 50,
#: issue #936). Any other format would be re-encoded to WebP by
#: ``convert_image_to_webp()`` on save, stripping those markings again.
GENERATED_IMAGE_FORMAT = "webp"

#: File extension for :data:`GENERATED_IMAGE_FORMAT`. The extension has to
#: travel with the bytes: ``upload_to`` keeps whatever suffix the saved name
#: carries, and ``convert_image_to_webp()`` decides from it whether a re-encode
#: is needed — a WebP saved as ``.png`` would be re-encoded and lose its
#: markings.
GENERATED_IMAGE_EXTENSION = f".{GENERATED_IMAGE_FORMAT}"

#: Instruction for the AI-disclosure label. The official icon travels with the
#: request as a reference image (see ``openai_image_bytes``).
AI_LABEL_PROMPT = (
    " Das beigefügte Referenzbild ist die EU-Kennzeichnung für KI-generierte"
    ' Inhalte (eine schwarze Pille mit dem weißen Text "AI GENERATED"). Es ist'
    " nicht das Motiv. Blende diese Kennzeichnung in der unteren rechten Ecke"
    " des Bildes ein, mit deutlichem Abstand zum Rand und etwa"
    f" {round(LABEL_WIDTH_RATIO * 100)} Prozent der Bildbreite breit. Übernimm"
    " sie exakt unverändert aus dem Referenzbild:"
    " gleiche Form, gleiche Proportionen, gleiche Schrift, gleiche Farben und"
    " gleicher Text. Sie ist scharf, vollständig sichtbar und verdeckt das"
    " zentrale Motiv nicht."
)


def build_image_prompt(
    word_text: str,
    unit_title: str | None = None,
    additional_info: str | None = None,
    job_title: str | None = None,
    allow_text_in_image: bool = False,
) -> str:
    """
    Build the German image-generation prompt shared by the on-demand admin
    view and the background import drain.

    Most vocabulary items look wrong with any text/numbers/logos in the
    picture (issue #918), so that's banned by default. Some items (a receipt,
    a clock face, a calendar) are inherently defined by the text/numbers on
    them, so ``allow_text_in_image`` lets an editor lift the ban for those.

    Every prompt ends with ``AI_LABEL_PROMPT``, the AI-disclosure label — the
    text ban has to exempt it explicitly, or the two instructions contradict
    each other.
    """
    prompt = (
        f"Ein realistisches, professionelles Foto, das eindeutig zeigt: {word_text}."
    )
    if job_title:
        prompt += f" Beruflicher Kontext: {job_title}."
    if unit_title:
        prompt += f" Thematischer Kontext: {unit_title}."
    prompt += (
        " Nur das zentrale Motiv ist zu sehen, vor einem neutralen weißen Hintergrund,"
        " ohne zusätzliche Objekte. Fotorealistisch, keine Illustration, kein Rendering."
    )
    if additional_info:
        prompt += f" Hinweise zur Bildgestaltung: {additional_info}."
    if not allow_text_in_image:
        prompt += (
            " Außer der unten beschriebenen Kennzeichnung enthält das Bild keinerlei"
            " Text, Buchstaben, Zahlen, Beschriftungen, Untertitel oder Logos."
        )
    prompt += AI_LABEL_PROMPT
    return prompt


def openai_image_bytes(prompt: str) -> bytes:
    """
    Call the OpenAI image edit API once, with the AI-disclosure label as the
    reference image, and return the raw bytes of the result.

    ``output_format`` is WebP, the format the CMS serves, so the file we store
    is byte-for-byte OpenAI's own output. Nothing re-encodes it afterwards, and
    the provenance markings OpenAI embeds (C2PA manifest, watermark) stay
    intact — a re-encode would strip them.
    """
    client = get_openai_client()
    ai_label = (LABEL_PATH.name, LABEL_PATH.read_bytes(), "image/png")
    # quality and output_format are env-configured str (LUNES_CMS_OPENAI_IMAGE_*),
    # which the SDK's overloads can't statically narrow to their Literal[...] type.
    response = client.images.edit(
        model=settings.OPENAI_IMAGE_MODEL,
        image=ai_label,
        prompt=prompt,
        size="1024x1024",
        quality=settings.OPENAI_IMAGE_QUALITY,  # type: ignore[call-overload]
        output_format=GENERATED_IMAGE_FORMAT,
        output_compression=settings.OPENAI_IMAGE_OUTPUT_COMPRESSION,
        n=1,
    )
    return base64.b64decode(response.data[0].b64_json)


def openai_word_image_bytes(word: Word, job_title: str | None = None) -> bytes:
    """
    Generate image bytes for a single word via the OpenAI image API.
    """
    return openai_image_bytes(build_image_prompt(word.word, job_title=job_title))


def _generate_for_word_image(word: Word, job_title: str | None = None) -> None:
    """
    Generate a missing image for a single Word and save it to the ImageField.

    The file is saved under the extension OpenAI encoded it in, so
    ``convert_image_to_webp()`` in ``Word.save()`` short-circuits and the bytes
    stay OpenAI's. The field defaults ``image_check_status`` to ``NOT_CHECKED``.
    The file name is the UUID the field's ``upload_to`` assigns — same as every
    other image in the system.
    """
    if not word.image:
        data = openai_word_image_bytes(word, job_title=job_title)
        word.image.save(
            f"image{GENERATED_IMAGE_EXTENSION}", ContentFile(data), save=False
        )
        word.save(image_source=ImageSource.AI_LABELED)
        logger.info("Generated image for word_id=%s (%s)", word.pk, word.word)


def _pending_filter(word_ids: list[int] | None = None) -> Q:
    pending = (Q(image="") | Q(image__isnull=True)) & ~Q(word="")
    if word_ids is not None:
        pending &= Q(pk__in=word_ids)
    return pending


def drain_pending_images(
    word_ids: list[int] | None = None,
    throttle_seconds: float = 1.0,
    job_title: str | None = None,
) -> None:
    """
    Process Words that need an image, one at a time, until none remain.

    ``word_ids`` restricts the drain to those Word rows (the ones a CSV
    import just created). Without it the whole table is scanned.

    ``job_title`` adds the importing job to every prompt in the batch. A CSV
    import always targets a single job, unlike already saved words which can
    belong to several jobs.

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
                _generate_for_word_image(word, job_title=job_title)
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
