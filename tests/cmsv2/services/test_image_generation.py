"""
Tests for the background image generation worker.
"""

import threading
from unittest import mock

import pytest
from django.core.files.base import ContentFile

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models import word as word_module
from lunes_cms.cmsv2.services import image_generation
from lunes_cms.cmsv2.utils import OpenAIConfigurationError


@pytest.fixture(autouse=True)
def _bypass_webp_conversion():
    """
    Word.save() runs ``convert_image_to_webp()`` (Pillow re-encodes the file)
    when an image is set. We feed dummy bytes through the worker, so skip the
    conversion step in tests.
    """
    with mock.patch.object(
        word_module, "convert_image_to_webp", lambda image_field: False
    ):
        yield


@pytest.fixture
def fast_worker(transactional_db, settings, tmp_path):
    """
    Strip the throttle so tests don't sleep, start from an empty Word table,
    and write media to an isolated temp dir.

    The worker scans the *whole* Word table. The session-scoped ``test_data``
    fixture plus ``transaction=True`` (no rollback between tests) can leave rows
    around, so wipe them first to keep these tests isolated. A per-test
    ``MEDIA_ROOT`` keeps generated files isolated across runs.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    Word.objects.all().delete()
    with mock.patch.object(image_generation, "time") as mocked_time:
        mocked_time.sleep = lambda _seconds: None
        yield


def _run_drain(word_ids=None):
    """
    Run the worker in a thread, like it runs in production.

    ``drain_pending_images`` calls ``connection.close()`` on exit (it returns
    the DB connection of its worker thread); calling it inline would close the
    *test's* connection. All worker tests are ``transaction=True`` so the
    worker thread sees committed data.
    """
    thread = threading.Thread(
        target=image_generation.drain_pending_images,
        kwargs={"word_ids": word_ids, "throttle_seconds": 0},
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
def test_drain_generates_image_for_word_missing_image(fast_worker):
    word = _make_word(word="Hammer")

    with mock.patch.object(
        image_generation, "openai_word_image_bytes", return_value=b"fake-png"
    ) as image_call:
        _run_drain()

    word.refresh_from_db()
    assert word.image
    assert word.image.read() == b"fake-png"
    assert image_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_stores_image_under_standard_path(fast_worker):
    word = _make_word(word="Säge & Co")

    with mock.patch.object(
        image_generation, "openai_word_image_bytes", return_value=b"fake-png"
    ):
        _run_drain()

    word.refresh_from_db()
    # Naming is delegated to the field's ``upload_to`` (a UUID under images/),
    # consistent with every other image in the system — never word-derived.
    assert word.image.name.startswith("images/")
    assert word.image.name.endswith(".png")
    assert "Säge" not in word.image.name


@pytest.mark.django_db(transaction=True)
def test_drain_is_idempotent_for_already_generated_words(fast_worker):
    word = _make_word(word="Hammer")
    word.image.save("hammer.png", ContentFile(b"existing"))
    word.refresh_from_db()

    with mock.patch.object(image_generation, "openai_word_image_bytes") as image_call:
        _run_drain()

    assert image_call.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_isolates_failures_per_row(fast_worker):
    failing = _make_word(word="Schraubenzieher")
    succeeding = _make_word(word="Säge")

    def maybe_fail(word: Word) -> bytes:
        if word.word == "Schraubenzieher":
            raise ValueError("simulated openai 5xx")
        return b"ok-png"

    with mock.patch.object(
        image_generation, "openai_word_image_bytes", side_effect=maybe_fail
    ):
        _run_drain()

    failing.refresh_from_db()
    succeeding.refresh_from_db()
    assert not failing.image
    assert succeeding.image.read() == b"ok-png"


@pytest.mark.django_db(transaction=True)
def test_drain_exits_quietly_when_openai_not_configured(fast_worker):
    _make_word(word="Hammer")

    with mock.patch.object(
        image_generation,
        "openai_word_image_bytes",
        side_effect=OpenAIConfigurationError("missing key"),
    ):
        # Should return without raising.
        _run_drain()


@pytest.mark.django_db(transaction=True)
def test_drain_skips_words_with_empty_word(fast_worker):
    Word.objects.create(word="", singular_article=0)

    with mock.patch.object(image_generation, "openai_word_image_bytes") as image_call:
        _run_drain()

    assert image_call.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_does_not_repick_a_failed_row(fast_worker):
    word = _make_word(word="Hammer")

    with mock.patch.object(
        image_generation,
        "openai_word_image_bytes",
        side_effect=ValueError("boom"),
    ) as image_call:
        _run_drain()

    word.refresh_from_db()
    assert not word.image
    # Tried exactly once this pass, then parked in failed_pks (no money-burning loop).
    assert image_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_only_processes_given_word_ids(fast_worker):
    imported = _make_word(word="Hammer")
    other = _make_word(word="Säge")

    with mock.patch.object(
        image_generation, "openai_word_image_bytes", return_value=b"png"
    ) as image_call:
        _run_drain(word_ids=[imported.pk])

    imported.refresh_from_db()
    other.refresh_from_db()
    assert imported.image.read() == b"png"
    assert not other.image
    assert image_call.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_is_single_flight(fast_worker):
    _make_word(word="Hammer")

    image_generation._drain_lock.acquire()  # pylint: disable=protected-access
    try:
        with mock.patch.object(
            image_generation, "openai_word_image_bytes"
        ) as image_call:
            # Lock already held -> should return immediately, doing nothing.
            _run_drain()
        assert image_call.call_count == 0
    finally:
        image_generation._drain_lock.release()  # pylint: disable=protected-access


def test_build_image_prompt_includes_word_and_optional_hints():
    bare = image_generation.build_image_prompt("Hammer")
    assert '"Hammer"' in bare
    assert "Lernmodul" not in bare

    enriched = image_generation.build_image_prompt(
        "Hammer", unit_title="Werkzeuge", additional_info="Profilansicht"
    )
    assert "Werkzeuge" in enriched
    assert "Profilansicht" in enriched
