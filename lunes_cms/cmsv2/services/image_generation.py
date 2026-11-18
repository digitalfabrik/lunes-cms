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
import json
import logging
import os
import threading
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import connection
from django.db.models import Q
from openai import RateLimitError

from ..models import AIGeneration, Area, ImagePrompt, Job, Unit, Word
from ..models.static import AIGenerationEvent, ImageSource
from ..utils import get_openai_client, OpenAIConfigurationError
from .ai_label import LABEL_PATH, LABEL_WIDTH_RATIO
from .show_people import resolve_show_people

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


#: Ban on text in the image, appended unless an editor allows text. It
#: exempts the AI label, or the two instructions would contradict each other.
TEXT_BAN_PROMPT = (
    " Außer der unten beschriebenen Kennzeichnung enthält das Bild keinerlei"
    " Text, Buchstaben, Zahlen, Beschriftungen, Untertitel oder Logos."
)


def build_image_prompt(  # pylint: disable=too-many-arguments
    word_text: str,
    unit_title: str | None = None,
    additional_info: str | None = None,
    job_title: str | None = None,
    allow_text_in_image: bool = False,
    *,
    image_prompt: ImagePrompt | None = None,
    show_people: bool = False,
) -> str:
    """
    Build the image-generation prompt from plain text.

    Callers generating an image for a word go through
    :func:`build_word_image_prompt`, which resolves the context to pass here.

    ``image_prompt`` is the stored prompt to render, the default one if
    ``None`` (#1143). ``show_people`` picks its variant if it has one with
    and one without people (#1145). Code appends the parts no stored prompt
    may drop:

    Most vocabulary items look wrong with any text/numbers/logos in the
    picture (issue #918), so ``TEXT_BAN_PROMPT`` bans that by default. Some
    items (a receipt, a clock face, a calendar) are inherently defined by the
    text/numbers on them, so ``allow_text_in_image`` lets an editor lift the
    ban for those.

    Every prompt ends with ``AI_LABEL_PROMPT``, the AI-disclosure label.
    """
    if image_prompt is None:
        image_prompt = ImagePrompt.get_default()
    prompt = image_prompt.render(
        word_text,
        job=job_title,
        unit=unit_title,
        additional_info=additional_info,
        show_people=show_people,
    )
    if not allow_text_in_image:
        prompt += TEXT_BAN_PROMPT
    prompt += AI_LABEL_PROMPT
    return prompt


def image_model() -> str:
    """
    The model images are generated with, which is stored with every
    generated image (#1145).
    """
    return settings.OPENAI_IMAGE_MODEL


def openai_image_bytes(prompt: str, area: Area) -> bytes:
    """
    Call the OpenAI image edit API once, with the AI-disclosure label as the
    reference image, and return the raw bytes of the result.

    ``output_format`` is WebP, the format the CMS serves, so the file we store
    is byte-for-byte OpenAI's own output. Nothing re-encodes it afterwards, and
    the provenance markings OpenAI embeds (C2PA manifest, watermark) stay
    intact — a re-encode would strip them.

    The generation is recorded for ``area``, the area of the content the
    image is generated for.
    """
    client = get_openai_client()
    ai_label = (LABEL_PATH.name, LABEL_PATH.read_bytes(), "image/png")
    # quality and output_format are env-configured str (LUNES_CMS_OPENAI_IMAGE_*),
    # which the SDK's overloads can't statically narrow to their Literal[...] type.
    response = client.images.edit(
        model=image_model(),
        image=ai_label,
        prompt=prompt,
        size="1024x1024",
        quality=settings.OPENAI_IMAGE_QUALITY,  # type: ignore[call-overload]
        output_format=GENERATED_IMAGE_FORMAT,
        output_compression=settings.OPENAI_IMAGE_OUTPUT_COMPRESSION,
        n=1,
    )
    AIGeneration.record(AIGenerationEvent.IMAGE, area)
    return base64.b64decode(response.data[0].b64_json)


@dataclass(frozen=True)
class ImagePromptContext:
    """
    The content an image prompt is built from: the word, plus the unit and the
    job it is shown in when those are unambiguous.
    """

    word: str
    unit_title: str | None
    job_title: str | None

    def prompt(
        self,
        additional_info: str | None = None,
        allow_text_in_image: bool = False,
        image_prompt: ImagePrompt | None = None,
        show_people: bool = False,
    ) -> str:
        """
        Build the image prompt for this context, from the default prompt
        unless ``image_prompt`` is given.
        """
        return build_image_prompt(
            self.word,
            unit_title=self.unit_title,
            additional_info=additional_info,
            job_title=self.job_title,
            allow_text_in_image=allow_text_in_image,
            image_prompt=image_prompt,
            show_people=show_people,
        )


def image_prompt_context(
    word: Word, *, unit: Unit | None = None, job: Job | None = None
) -> ImagePromptContext:
    """
    Resolve the unit and job an image prompt for ``word`` mentions.

    Callers pass what they know: a unit<>word relation knows its unit, a CSV
    import its job. Whatever is missing is derived from the word's units, but
    only when that leaves exactly one candidate. A picture has to show one
    concrete thing, so several jobs are left out instead of listed (#824).
    Fetching 2 (LIMIT 2) is enough to tell "exactly one" from "more than one".
    """
    if unit is None:
        units = word.units.all()
        if job is not None:
            units = units.filter(jobs=job)
        unit_candidates = list(units[:2])
        unit = unit_candidates[0] if len(unit_candidates) == 1 else None
    if job is None:
        jobs = (
            unit.jobs.all()
            if unit is not None
            else Job.objects.filter(units__words=word).distinct()
        )
        job_candidates = list(jobs[:2])
        job = job_candidates[0] if len(job_candidates) == 1 else None
    return ImagePromptContext(
        word=word.word,
        unit_title=unit.title if unit is not None else None,
        job_title=job.name if job is not None else None,
    )


def build_word_image_prompt(  # pylint: disable=too-many-arguments
    word: Word,
    *,
    unit: Unit | None = None,
    job: Job | None = None,
    additional_info: str | None = None,
    allow_text_in_image: bool = False,
    image_prompt: ImagePrompt | None = None,
    show_people: bool | None = None,
) -> str:
    """
    Build the image prompt for ``word``, the one entry point for every place
    that generates a word image, so they all send the same context.

    See :func:`image_prompt_context` for how ``unit`` and ``job`` are resolved.
    ``image_prompt`` is the stored prompt to render, the default one if
    ``None``.

    ``show_people`` picks the variant of a prompt that supports show people.
    If it is ``None``, the word's stored decision is used, and a word without
    one is classified first (see :func:`resolve_show_people`), so this must
    not run inside a transaction.
    """
    if image_prompt is None:
        image_prompt = ImagePrompt.get_default()
    context = image_prompt_context(word, unit=unit, job=job)
    if show_people is None:
        show_people = resolve_show_people(word, image_prompt, context)
    return context.prompt(
        additional_info, allow_text_in_image, image_prompt, show_people
    )


def generation_record_path(temp_image_path: str) -> str:
    """
    The file next to a temporarily stored generated image that records the
    prompt and model it was generated with, until an editor stores it.
    """
    return f"{temp_image_path}.json"


def write_generation_record(
    temp_image_path: str, image_prompt: ImagePrompt, model: str
) -> None:
    """
    Record which prompt and model a temporarily stored image was generated
    with, see :func:`read_generation_record`.
    """
    with open(generation_record_path(temp_image_path), "w", encoding="utf-8") as f:
        json.dump({"image_prompt": image_prompt.pk, "image_model": model}, f)


def read_generation_record(temp_image_path: str) -> tuple[ImagePrompt | None, str]:
    """
    The prompt and model a temporarily stored image was generated with, and
    remove their record.

    Both are empty if nothing was recorded, e.g. for an image generated before
    the record existed.
    """
    record_path = generation_record_path(temp_image_path)
    try:
        with open(record_path, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError):
        return None, ""
    os.remove(record_path)
    if not isinstance(record, dict):
        return None, ""
    prompt_id = record.get("image_prompt")
    image_prompt = (
        ImagePrompt.objects.filter(pk=prompt_id).first()
        if isinstance(prompt_id, int)
        else None
    )
    model = record.get("image_model")
    return image_prompt, model if isinstance(model, str) else ""


def _generate_for_word_image(word: Word, job: Job | None = None) -> None:
    """
    Generate a missing image for a single Word and save it to the ImageField.

    The file is saved under the extension OpenAI encoded it in, so
    ``convert_image_to_webp()`` in ``Word.save()`` short-circuits and the bytes
    stay OpenAI's. The field defaults ``image_check_status`` to ``NOT_CHECKED``.
    The file name is the UUID the field's ``upload_to`` assigns — same as every
    other image in the system.

    A word whose image prompt supports show people and that has no decision
    yet is classified first (#1145); both OpenAI calls run outside any
    transaction. The image records the prompt and model it was made with.
    """
    if not word.image:
        image_prompt = ImagePrompt.get_default()
        data = openai_image_bytes(
            build_word_image_prompt(word, job=job, image_prompt=image_prompt),
            word.area,
        )
        image_prompt.mark_used()
        word.image_prompt = image_prompt
        word.image_model = image_model()
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
    job: Job | None = None,
) -> None:
    """
    Process Words that need an image, one at a time, until none remain.

    ``word_ids`` restricts the drain to those Word rows (the ones a CSV
    import just created). Without it the whole table is scanned.

    ``job`` is the importing job. A CSV import always targets a single job,
    unlike already saved words which can belong to several jobs, and it also
    picks the word's unit within that job for the prompt.

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
                _generate_for_word_image(word, job=job)
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
