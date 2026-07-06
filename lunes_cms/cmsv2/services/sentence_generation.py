"""
Example sentence generation for Word objects via OpenAI.

Besides the on-demand admin endpoints, this module provides a background drain
(mirroring ``audio_generation`` / ``image_generation``): a Word created by a CSV
import that has an empty ``example_sentence`` is "pending"; a worker thread picks
pending rows, asks OpenAI for a sentence, and saves it. It is triggered from
``import_csv_view`` *before* the audio drain, so the generated sentence gets its
own audio in the same import.
"""

import logging
import threading
import time

from django.conf import settings
from django.db import connection
from django.db.models import Q
from openai import RateLimitError

from ..models import Job, Word
from ..utils import get_openai_client, OpenAIConfigurationError

logger = logging.getLogger(__name__)

_drain_lock = threading.Lock()


def build_example_sentence_prompt(word: str, job: str, unit: str | None = None) -> str:
    """
    Build the German prompt for generating an example sentence.

    Args:
        word: The vocabulary term the sentence is about
        job: The job (or comma-separated jobs) providing the professional context
        unit: Optional title of the learning unit for unit<>word relations

    Returns:
        str: The prompt to send to OpenAI
    """
    context = f"im Rahmen des Berufs {job}"
    if unit:
        context += f" und der Lerneinheit {unit}"
    return (
        "Für eine interaktive Übung in einer Vokabel-Lern-App benötige ich "
        f"einen Beispielsatz für den Fachbegriff {word} {context}. "
        "Es können Aussagesätze, Fragesätze oder Aufforderungssätze sein. "
        "Der Fachbegriff soll nicht immer am Satzanfang stehen. "
        "Der Beispielsatz sollte aus dem Arbeitsalltag des vorher genannten "
        "Berufes stammen. Das Sprachniveau der Sätze soll hauptsächlich für "
        "Lernende mit Deutsch als Zweitsprache (B1) passen, aber es dürfen "
        "auch ein paar B2 Niveau Sätze sein. Sätze eher kürzer halten "
        "(5-10 Wörter). "
        "Antworte ausschließlich mit dem Beispielsatz, ohne Anführungszeichen "
        "und ohne zusätzliche Erklärungen."
    )


def openai_example_sentence(word: str, job: str, unit: str | None = None) -> str:
    """
    Generate a single example sentence for a vocabulary term via OpenAI.

    Args:
        word: The vocabulary term the sentence is about
        job: The job (or comma-separated jobs) providing the professional context
        unit: Optional title of the learning unit for unit<>word relations

    Returns:
        str: The generated example sentence

    Raises:
        ValueError: If OpenAI returns an empty response
    """
    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_TEXT_MODEL,
        messages=[
            {
                "role": "user",
                "content": build_example_sentence_prompt(word, job, unit),
            }
        ],
    )
    sentence = (response.choices[0].message.content or "").strip()
    # The prompt asks for the bare sentence, but strip stray quotes anyway.
    sentence = sentence.strip("\"'„“‚‘»«").strip()
    if not sentence:
        raise ValueError("OpenAI returned an empty example sentence.")
    return sentence


def _job_context_for_word(word: Word, job_title: str | None) -> str:
    """
    Determine the professional context for a word's example sentence.

    A CSV import targets a single job and passes it via ``job_title``. Without
    it (generic drain), the context is derived from every job the word's units
    belong to — same logic as the on-demand word endpoint.
    """
    if job_title:
        return job_title
    job_names = list(
        Job.objects.filter(units__words=word)
        .distinct()
        .order_by("name")
        .values_list("name", flat=True)
    )
    return ", ".join(job_names)


def _generate_for_word_sentence(word: Word, job_title: str | None = None) -> bool:
    """
    Generate and save a missing example sentence for a single Word.

    Returns True if a sentence was generated and saved, False if the word was
    skipped (already has a sentence, or no job context to build a prompt from).
    """
    if word.example_sentence and word.example_sentence.strip():
        return False
    job = _job_context_for_word(word, job_title)
    if not job:
        logger.info(
            "Skipping sentence generation for word_id=%s (%s) — no job context",
            word.pk,
            word.word,
        )
        return False
    unit_title = word.units.values_list("title", flat=True).first()
    sentence = openai_example_sentence(word.word, job, unit_title)
    word.example_sentence = sentence
    # ``Word.save()`` flips ``example_sentence_check_status`` to NOT_CHECKED when
    # the sentence changes, so it must be in ``update_fields`` to be persisted.
    word.save(update_fields=["example_sentence", "example_sentence_check_status"])
    logger.info("Generated example sentence for word_id=%s (%s)", word.pk, word.word)
    return True


def _pending_sentence_filter(word_ids: list[int] | None = None) -> Q:
    pending = (Q(example_sentence="") | Q(example_sentence__isnull=True)) & ~Q(word="")
    if word_ids is not None:
        pending &= Q(pk__in=word_ids)
    return pending


def drain_pending_sentences(
    word_ids: list[int] | None = None,
    throttle_seconds: float = 1.0,
    job_title: str | None = None,
) -> None:
    """
    Process Words that need an example sentence, one at a time, until none remain.

    ``word_ids`` restricts the drain to those Word rows (the ones a CSV import
    just created). ``job_title`` supplies the single job a CSV import targets.

    Mirrors the audio/image drains: single-flight within the process, per-row
    failure isolation, and a back-off on rate limits. Triggered from
    ``import_csv_view`` *before* the audio drain so generated sentences get audio.
    """
    # Non-blocking single-flight guard; released in the finally below.
    if not _drain_lock.acquire(blocking=False):  # pylint: disable=consider-using-with
        return
    failed_pks: set[int] = set()
    try:
        pending = Word.objects.filter(_pending_sentence_filter(word_ids)).count()
        logger.info(
            "Sentence drain starting: %s word(s) pending — "
            "up to %s OpenAI request(s)",
            pending,
            pending,
        )
        while True:
            word = (
                Word.objects.filter(_pending_sentence_filter(word_ids))
                .exclude(pk__in=failed_pks)
                .first()
            )
            if word is None:
                return
            try:
                generated = _generate_for_word_sentence(word, job_title=job_title)
            except OpenAIConfigurationError:
                logger.warning("OpenAI not configured — sentence worker exiting")
                return
            except RateLimitError:
                # Org RPM limit hit. Back off and retry the same row — the
                # SDK already did its own short retries before raising.
                logger.warning("OpenAI rate limit — backing off 30s")
                time.sleep(30)
                continue
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Sentence generation failed for word_id=%s — leaving for retry",
                    word.pk,
                )
                # Don't re-pick this row in this pass; it'll be retried on the
                # next drain (import / app restart).
                failed_pks.add(word.pk)
                continue
            if not generated:
                # Skipped (no job context) but still matches the pending filter;
                # park it so the loop doesn't spin on the same row forever.
                failed_pks.add(word.pk)
                continue
            time.sleep(throttle_seconds)
    finally:
        _drain_lock.release()
        connection.close()
