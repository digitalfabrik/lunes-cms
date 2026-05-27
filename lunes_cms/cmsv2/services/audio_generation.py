"""
Background audio generation for Word objects.

The DB itself is the queue: a Word with empty ``audio`` (or empty
``example_sentence_audio`` while ``example_sentence`` is set) is "pending".
A worker thread picks pending rows, calls OpenAI TTS, saves the file.
Idempotent — already-populated rows are filtered out, so re-runs are free.

The drain is scoped to the word IDs just created by a CSV import (passed via
``word_ids``); it never touches words created elsewhere. So an import only
generates audio for its own rows, not for the whole table.

The OpenAI call (several seconds) is made *outside* any DB transaction, so a
slow request never holds a write lock. An in-process lock makes the drain
single-flight, so two imports in quick succession don't kick off overlapping
workers.

Triggered from ``import_csv_view`` after a successful CSV import. If a worker
dies mid-batch (process crash, OOM, deploy), the remaining rows stay pending
and will be picked up on the next import. If that ever becomes a real problem
we should switch to a persistent queue (e.g. Celery).
"""

import logging
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


def openai_word_audio_bytes(text: str) -> bytes:
    """
    Generate mp3 bytes for a single word/term via OpenAI TTS.
    """
    client = get_openai_client()
    response = client.audio.speech.create(
        model=settings.OPENAI_TTS_WORD_MODEL,
        voice=settings.OPENAI_TTS_VOICE,
        input=text,
    )
    return b"".join(response.iter_bytes(chunk_size=4096))


def openai_sentence_audio_bytes(sentence: str) -> bytes:
    """
    Generate mp3 bytes for an example sentence via OpenAI TTS.

    Picks intonation hint from sentence ending so questions sound like questions.
    """
    if sentence.strip().endswith("?"):
        instruction = "Read this sentence as a question with rising intonation."
    else:
        instruction = "Read this sentence as a declarative statement with neutral, falling intonation."
    client = get_openai_client()
    response = client.audio.speech.create(
        model=settings.OPENAI_TTS_SENTENCE_MODEL,
        voice=settings.OPENAI_TTS_VOICE,
        input=sentence,
        instructions=instruction,
    )
    return b"".join(response.iter_bytes(chunk_size=4096))


def _generate_for_word(word: Word) -> None:
    """
    Generate any missing audio for a single Word and save it to the FileField.

    Each ``FileField.save()`` runs its own short transaction (and triggers
    ``Word.save()`` -> ``convert_audio()``); the slow OpenAI calls happen
    between them, holding no lock.
    """
    if not word.audio:
        text = f"{word.singular_article_for_audio_generation()} {word.word}".strip()
        data = openai_word_audio_bytes(text)
        word.audio.save(
            f"{make_safe_filename(word.word)}.mp3",
            ContentFile(data),
        )
        logger.info("Generated word audio for word_id=%s (%s)", word.pk, word.word)

    if word.example_sentence and not word.example_sentence_audio:
        data = openai_sentence_audio_bytes(word.example_sentence)
        word.example_sentence_audio_regenerated = True
        word.example_sentence_audio.save(
            f"{make_safe_filename(word.word)}_example_sentence.mp3",
            ContentFile(data),
        )
        logger.info(
            "Generated example-sentence audio for word_id=%s (%s)", word.pk, word.word
        )


def _pending_filter(word_ids: list[int] | None = None) -> Q:
    needs_word_audio = Q(audio="") | Q(audio__isnull=True)
    needs_sentence_audio = ~Q(example_sentence="") & (
        Q(example_sentence_audio="") | Q(example_sentence_audio__isnull=True)
    )
    pending = (needs_word_audio | needs_sentence_audio) & ~Q(word="")
    if word_ids is not None:
        pending &= Q(pk__in=word_ids)
    return pending


def drain_pending_audio(
    word_ids: list[int] | None = None, throttle_seconds: float = 1.0
) -> None:
    """
    Process Words that need audio, one at a time, until none remain.

    ``word_ids`` restricts the drain to those Word rows (the ones a CSV
    import just created). Without it the whole table is scanned.

    Single-flight within the process: if another thread already holds the
    drain lock this call returns immediately (that thread will pick up
    anything we just queued).

    Failures on a single row are logged and the loop continues — the row's
    audio field stays empty so it'll be picked up on the next pass.
    """
    # Non-blocking single-flight guard; released in the finally below.
    if not _drain_lock.acquire(blocking=False):  # pylint: disable=consider-using-with
        return
    failed_pks: set[int] = set()
    scope = Q(pk__in=word_ids) if word_ids is not None else Q()
    try:
        missing_word_audio = Word.objects.filter(
            (Q(audio="") | Q(audio__isnull=True)) & ~Q(word="") & scope
        ).count()
        missing_sentence_audio = Word.objects.filter(
            ~Q(example_sentence="")
            & (Q(example_sentence_audio="") | Q(example_sentence_audio__isnull=True))
            & ~Q(word="")
            & scope
        ).count()
        pending = Word.objects.filter(_pending_filter(word_ids)).count()
        logger.info(
            "Audio drain starting: %s word(s) pending "
            "(%s missing word audio, %s missing example-sentence audio) — "
            "up to %s OpenAI TTS request(s)",
            pending,
            missing_word_audio,
            missing_sentence_audio,
            missing_word_audio + missing_sentence_audio,
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
                _generate_for_word(word)
            except OpenAIConfigurationError:
                logger.warning("OpenAI not configured — audio worker exiting")
                return
            except RateLimitError:
                # Org RPM limit hit. Back off and retry the same row — the
                # SDK already did its own short retries before raising.
                logger.warning("OpenAI rate limit — backing off 30s")
                time.sleep(30)
                continue
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Audio generation failed for word_id=%s — leaving for retry",
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
