"""
Tests for example sentence generation via OpenAI.
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest
from django.conf import settings

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.services import sentence_generation
from lunes_cms.cmsv2.utils import OpenAIConfigurationError


def _fake_openai_client(
    content: str | None = "Der Hammer liegt auf der Werkbank.",
) -> mock.Mock:
    fake_message = mock.Mock()
    fake_message.content = content
    fake_choice = mock.Mock()
    fake_choice.message = fake_message
    fake_response = mock.Mock()
    fake_response.choices = [fake_choice]
    fake_client = mock.Mock()
    fake_client.chat.completions.create.return_value = fake_response
    return fake_client


def test_prompt_contains_word_and_job() -> None:
    prompt = sentence_generation.build_example_sentence_prompt("Hammer", "Tischler")
    assert "Fachbegriff Hammer" in prompt
    assert "im Rahmen des Berufs Tischler" in prompt
    assert "Lerneinheit" not in prompt
    assert "B1" in prompt
    assert "5-10 Wörter" in prompt


def test_prompt_contains_unit_when_given() -> None:
    prompt = sentence_generation.build_example_sentence_prompt(
        "Hammer", "Tischler", "Werkzeuge"
    )
    assert "im Rahmen des Berufs Tischler und der Lerneinheit Werkzeuge" in prompt


def test_generation_uses_text_model_and_returns_sentence() -> None:
    fake_client = _fake_openai_client()

    with mock.patch.object(
        sentence_generation, "get_openai_client", return_value=fake_client
    ):
        sentence = sentence_generation.openai_example_sentence("Hammer", "Tischler")

    assert sentence == "Der Hammer liegt auf der Werkbank."
    create_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert create_kwargs["model"] == settings.OPENAI_TEXT_MODEL
    assert "Fachbegriff Hammer" in create_kwargs["messages"][0]["content"]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('"Der Hammer ist schwer."', "Der Hammer ist schwer."),
        ("„Der Hammer ist schwer.“", "Der Hammer ist schwer."),
        ("  Der Hammer ist schwer.  ", "Der Hammer ist schwer."),
    ],
)
def test_generation_strips_quotes_and_whitespace(raw: str, expected: str) -> None:
    fake_client = _fake_openai_client(content=raw)

    with mock.patch.object(
        sentence_generation, "get_openai_client", return_value=fake_client
    ):
        assert (
            sentence_generation.openai_example_sentence("Hammer", "Tischler")
            == expected
        )


@pytest.mark.parametrize("content", [None, "", '""'])
def test_generation_raises_on_empty_response(content: str | None) -> None:
    fake_client = _fake_openai_client(content=content)

    with mock.patch.object(
        sentence_generation, "get_openai_client", return_value=fake_client
    ):
        with pytest.raises(ValueError):
            sentence_generation.openai_example_sentence("Hammer", "Tischler")


# ---------------------------------------------------------------------------
# Background drain (CSV import)
# ---------------------------------------------------------------------------


@pytest.fixture
def fast_worker(transactional_db: None) -> Generator[None, None, None]:
    """
    Strip the throttle so tests don't sleep, and start from an empty Word table.

    The worker scans the *whole* Word table. The session-scoped ``test_data``
    fixture plus ``transaction=True`` (no rollback between tests) can leave rows
    around, so wipe them first to keep these tests isolated.
    """
    Word.objects.all().delete()
    with mock.patch.object(sentence_generation, "time") as mocked_time:
        mocked_time.sleep = lambda _seconds: None
        yield


def _run_drain(word_ids: list[int] | None = None, job_title: str | None = None) -> None:
    """
    Run the worker in a thread, like it runs in production.

    ``drain_pending_sentences`` calls ``connection.close()`` on exit (it returns
    the DB connection of its worker thread); calling it inline would close the
    *test's* connection. All worker tests are ``transaction=True`` so the worker
    thread sees committed data.
    """
    thread = threading.Thread(
        target=sentence_generation.drain_pending_sentences,
        kwargs={
            "word_ids": word_ids,
            "throttle_seconds": 0,
            "job_title": job_title,
        },
    )
    thread.start()
    thread.join(timeout=10)
    assert not thread.is_alive()


def _make_word(**overrides: Any) -> Word:
    defaults: dict[str, Any] = {"word": "Hammer", "singular_article": 1}
    defaults.update(overrides)
    return Word.objects.create(**defaults)


@pytest.mark.django_db(transaction=True)
def test_drain_generates_sentence_with_job_title(fast_worker: None) -> None:
    word = _make_word(word="Hammer")

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        return_value="Der Hammer liegt auf der Werkbank.",
    ) as gen:
        _run_drain(job_title="Tischler")

    word.refresh_from_db()
    assert word.example_sentence == "Der Hammer liegt auf der Werkbank."
    assert word.example_sentence_check_status == "NOT_CHECKED"
    assert gen.call_count == 1
    # word, job passed positionally
    assert gen.call_args[0][0] == "Hammer"
    assert gen.call_args[0][1] == "Tischler"


@pytest.mark.django_db(transaction=True)
def test_drain_skips_word_that_already_has_a_sentence(fast_worker: None) -> None:
    _make_word(word="Hammer", example_sentence="Schon vorhanden.")

    with mock.patch.object(sentence_generation, "openai_example_sentence") as gen:
        _run_drain(job_title="Tischler")

    assert gen.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_passes_unit_title_to_generation(fast_worker: None) -> None:
    job = Job.objects.create(name="Tischler")
    unit = Unit.objects.create(title="Werkzeuge")
    unit.jobs.add(job)
    word = _make_word(word="Hammer")
    unit.words.add(word)

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        return_value="Ein Satz.",
    ) as gen:
        _run_drain(job_title="Tischler")

    assert gen.call_args[0][2] == "Werkzeuge"


@pytest.mark.django_db(transaction=True)
def test_drain_derives_job_from_units_when_no_job_title(fast_worker: None) -> None:
    job = Job.objects.create(name="Maler")
    unit = Unit.objects.create(title="Farben")
    unit.jobs.add(job)
    word = _make_word(word="Pinsel")
    unit.words.add(word)

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        return_value="Ein Satz.",
    ) as gen:
        _run_drain()

    assert gen.call_count == 1
    assert gen.call_args[0][1] == "Maler"


@pytest.mark.django_db(transaction=True)
def test_drain_skips_word_without_job_context(fast_worker: None) -> None:
    word = _make_word(word="Hammer")

    with mock.patch.object(sentence_generation, "openai_example_sentence") as gen:
        # No job_title and no units -> no context, must not loop forever.
        _run_drain()

    word.refresh_from_db()
    assert gen.call_count == 0
    assert word.example_sentence == ""


@pytest.mark.django_db(transaction=True)
def test_drain_only_processes_given_word_ids(fast_worker: None) -> None:
    imported = _make_word(word="Hammer")
    other = _make_word(word="Säge")

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        return_value="Ein Satz.",
    ) as gen:
        _run_drain(word_ids=[imported.pk], job_title="Tischler")

    imported.refresh_from_db()
    other.refresh_from_db()
    assert imported.example_sentence == "Ein Satz."
    assert other.example_sentence == ""
    assert gen.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_isolates_failures_per_row(fast_worker: None) -> None:
    failing = _make_word(word="Schraubenzieher")
    succeeding = _make_word(word="Säge")

    def maybe_fail(word: str, _job: str, _unit: str | None = None) -> str:
        if word == "Schraubenzieher":
            raise ValueError("simulated openai 5xx")
        return "Ein Satz."

    with mock.patch.object(
        sentence_generation, "openai_example_sentence", side_effect=maybe_fail
    ):
        _run_drain(job_title="Tischler")

    failing.refresh_from_db()
    succeeding.refresh_from_db()
    assert failing.example_sentence == ""
    assert succeeding.example_sentence == "Ein Satz."


@pytest.mark.django_db(transaction=True)
def test_drain_does_not_repick_a_failed_row(fast_worker: None) -> None:
    word = _make_word(word="Hammer")

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        side_effect=ValueError("boom"),
    ) as gen:
        _run_drain(job_title="Tischler")

    word.refresh_from_db()
    assert word.example_sentence == ""
    # Tried exactly once, then parked in failed_pks (no money-burning loop).
    assert gen.call_count == 1


@pytest.mark.django_db(transaction=True)
def test_drain_exits_quietly_when_openai_not_configured(fast_worker: None) -> None:
    _make_word(word="Hammer")

    with mock.patch.object(
        sentence_generation,
        "openai_example_sentence",
        side_effect=OpenAIConfigurationError("missing key"),
    ):
        # Should return without raising.
        _run_drain(job_title="Tischler")


@pytest.mark.django_db(transaction=True)
def test_drain_skips_words_with_empty_word(fast_worker: None) -> None:
    Word.objects.create(word="", singular_article=0)

    with mock.patch.object(sentence_generation, "openai_example_sentence") as gen:
        _run_drain(job_title="Tischler")

    assert gen.call_count == 0


@pytest.mark.django_db(transaction=True)
def test_drain_is_single_flight(fast_worker: None) -> None:
    _make_word(word="Hammer")

    sentence_generation._drain_lock.acquire()  # pylint: disable=protected-access
    try:
        with mock.patch.object(sentence_generation, "openai_example_sentence") as gen:
            # Lock already held -> should return immediately, doing nothing.
            _run_drain(job_title="Tischler")
        assert gen.call_count == 0
    finally:
        sentence_generation._drain_lock.release()  # pylint: disable=protected-access
