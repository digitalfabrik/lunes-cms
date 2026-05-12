"""
Tests for the background audio generation worker.
"""

import threading
from unittest import mock

import pytest
from django.core.files.base import ContentFile

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.services import audio_generation
from lunes_cms.cmsv2.utils import OpenAIConfigurationError


@pytest.fixture(autouse=True)
def _bypass_audio_conversion():
    """
    Word.save() runs ``convert_audio()`` (pydub re-encodes the mp3) when an
    audio file is set. We feed dummy bytes through the worker, so skip the
    conversion step in tests.
    """
    with mock.patch.object(Word, "convert_audio", lambda self: None):
        yield


@pytest.fixture
def fast_worker(transactional_db):
    """
    Strip the throttle so tests don't sleep, and start from an empty Word table.

    The worker scans the *whole* Word table. The session-scoped ``test_data``
    fixture plus ``transaction=True`` (no rollback between tests) can leave rows
    around, so wipe them first to keep these tests isolated.
    """
    Word.objects.all().delete()
    with mock.patch.object(audio_generation, "time") as mocked_time:
        mocked_time.sleep = lambda _seconds: None
        yield


def _run_drain():
    """
    Run the worker in a thread, like it runs in production.

    ``drain_pending_audio`` calls ``connection.close()`` on exit (it returns the
    DB connection of its worker thread); calling it inline would close the
    *test's* connection. All worker tests are ``transaction=True`` so the worker
    thread sees committed data.
    """
    thread = threading.Thread(
        target=audio_generation.drain_pending_audio, kwargs={"throttle_seconds": 0}
    )
    thread.start()
    thread.join(timeout=10)
    assert not thread.is_alive()


def _make_word(**overrides) -> Word:
    defaults = {
        "word": "Hammer",
        "singular_article": 1,
    }
    defaults.update(overrides)
    return Word.objects.create(**defaults)


@pytest.mark.django_db(transaction=True)
def test_drain_generates_audio_for_word_missing_audio(fast_worker):
    word = _make_word(word="Hammer")

    with mock.patch.object(
        audio_generation, "openai_word_audio_bytes", return_value=b"fake-mp3"
    ) as word_audio_call:
        _run_drain()

    word.refresh_from_db()
    assert word.audio
    assert word.audio.read() == b"fake-mp3"
    assert word_audio_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_generates_sentence_audio_when_example_present(fast_worker):
    word = _make_word(word="Hammer", example_sentence="Der Hammer ist schwer.")

    with (
        mock.patch.object(
            audio_generation, "openai_word_audio_bytes", return_value=b"fake-word-mp3"
        ),
        mock.patch.object(
            audio_generation,
            "openai_sentence_audio_bytes",
            return_value=b"fake-sentence-mp3",
        ) as sentence_call,
    ):
        _run_drain()

    word.refresh_from_db()
    assert word.audio.read() == b"fake-word-mp3"
    assert word.example_sentence_audio.read() == b"fake-sentence-mp3"
    assert word.example_sentence_audio_regenerated is True
    assert sentence_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_is_idempotent_for_already_generated_words(fast_worker):
    word = _make_word(word="Hammer")
    word.audio.save("hammer.mp3", ContentFile(b"existing"))
    word.refresh_from_db()

    with (
        mock.patch.object(
            audio_generation, "openai_word_audio_bytes"
        ) as word_audio_call,
        mock.patch.object(
            audio_generation, "openai_sentence_audio_bytes"
        ) as sentence_call,
    ):
        _run_drain()

    assert word_audio_call.call_count == 0
    assert sentence_call.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_isolates_failures_per_row(fast_worker):
    failing = _make_word(word="Schraubenzieher")
    succeeding = _make_word(word="Säge")

    def maybe_fail(text: str) -> bytes:
        if "Schraubenzieher" in text:
            raise ValueError("simulated openai 5xx")
        return b"ok-mp3"

    with mock.patch.object(
        audio_generation, "openai_word_audio_bytes", side_effect=maybe_fail
    ):
        _run_drain()

    failing.refresh_from_db()
    succeeding.refresh_from_db()
    assert not failing.audio
    assert succeeding.audio.read() == b"ok-mp3"


@pytest.mark.django_db(transaction=True)
def test_drain_exits_quietly_when_openai_not_configured(fast_worker):
    _make_word(word="Hammer")

    with mock.patch.object(
        audio_generation,
        "openai_word_audio_bytes",
        side_effect=OpenAIConfigurationError("missing key"),
    ):
        # Should return without raising.
        _run_drain()


@pytest.mark.django_db(transaction=True)
def test_drain_picks_word_missing_only_sentence_audio(fast_worker):
    word = _make_word(word="Hammer", example_sentence="Der Hammer ist schwer.")
    word.audio.save("hammer.mp3", ContentFile(b"existing"))
    word.refresh_from_db()

    with (
        mock.patch.object(
            audio_generation, "openai_word_audio_bytes"
        ) as word_audio_call,
        mock.patch.object(
            audio_generation,
            "openai_sentence_audio_bytes",
            return_value=b"sentence-mp3",
        ) as sentence_call,
    ):
        _run_drain()

    word.refresh_from_db()
    assert word_audio_call.call_count == 0
    assert sentence_call.call_count == 1
    assert word.example_sentence_audio.read() == b"sentence-mp3"


@pytest.mark.django_db(transaction=True)
def test_drain_skips_words_with_empty_word(fast_worker):
    Word.objects.create(word="", singular_article=0)

    with mock.patch.object(
        audio_generation, "openai_word_audio_bytes"
    ) as word_audio_call:
        _run_drain()

    assert word_audio_call.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_does_not_repick_a_failed_row(fast_worker):
    word = _make_word(word="Hammer")

    with mock.patch.object(
        audio_generation,
        "openai_word_audio_bytes",
        side_effect=ValueError("boom"),
    ) as word_audio_call:
        _run_drain()

    word.refresh_from_db()
    assert not word.audio
    # Tried exactly once this pass, then parked in failed_pks (no money-burning loop).
    assert word_audio_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_is_single_flight(fast_worker):
    _make_word(word="Hammer")

    audio_generation._drain_lock.acquire()  # pylint: disable=protected-access
    try:
        with mock.patch.object(
            audio_generation, "openai_word_audio_bytes"
        ) as word_audio_call:
            # Lock already held -> should return immediately, doing nothing.
            _run_drain()
        assert word_audio_call.call_count == 0
    finally:
        audio_generation._drain_lock.release()  # pylint: disable=protected-access


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("Hammer.mp3", "audio/Hammer.mp3"),
        ("Hammer-conv.mp3", "audio/Hammer.mp3"),
        ("some/dir/Sägeblatt.wav", "audio/Sägeblatt.mp3"),
        ("with space&punct!.mp3", "audio/with_space_punct_.mp3"),
        ("", "audio/audio.mp3"),
    ],
)
def test_convert_umlaute_audio_keeps_word_name(filename, expected):
    from lunes_cms.cmsv2.models.static import convert_umlaute_audio

    assert convert_umlaute_audio(None, filename) == expected
