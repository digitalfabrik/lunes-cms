"""
Tests for deciding per word whether generated images show people (#1145).
"""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest import mock

import pytest
from openai import OpenAIError
from pytest_django import Settings

from lunes_cms.cmsv2.models import ImagePrompt, Job, Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.services import show_people
from lunes_cms.cmsv2.services.image_generation import (
    build_word_image_prompt,
    image_prompt_context,
    ImagePromptContext,
)
from lunes_cms.cmsv2.utils import OpenAIConfigurationError

CONTEXT = ImagePromptContext(word="Beratung", unit_title="Kunden", job_title="Bank")


def people_prompt(**overrides: object) -> ImagePrompt:
    """
    A default prompt with show-people variants that are easy to tell apart.
    """
    fields: dict[str, object] = {
        "name": "Mit Personen",
        "supports_show_people": True,
        "prompt_with_people": "MIT {{ word }}",
        "prompt_without_people": "OHNE {{ word }}",
        "is_default": True,
    }
    fields.update(overrides)
    return ImagePrompt.objects.create(**fields)


def classifier_answer(content: str) -> mock.MagicMock:
    """
    An OpenAI client whose chat completion answers with ``content``.
    """
    client = mock.MagicMock()
    client.chat.completions.create.return_value.choices = [
        mock.MagicMock(message=mock.MagicMock(content=content))
    ]
    return client


@pytest.fixture
def classifier() -> Generator[mock.MagicMock, None, None]:
    """
    A classifier that decides to show people.
    """
    client = classifier_answer(json.dumps({"show_people": True}))
    with mock.patch.object(show_people, "get_openai_client", return_value=client):
        yield client


@pytest.mark.parametrize("decision", [True, False])
def test_classify_returns_the_decision_of_the_model(decision: bool) -> None:
    client = classifier_answer(json.dumps({"show_people": decision}))
    with mock.patch.object(show_people, "get_openai_client", return_value=client):
        assert show_people.classify_show_people(CONTEXT) is decision


def test_classify_sends_the_word_and_its_context_to_the_classifier_model(
    classifier: mock.MagicMock, settings: Settings
) -> None:
    settings.OPENAI_CLASSIFIER_MODEL = "small-model"

    show_people.classify_show_people(CONTEXT)

    kwargs = classifier.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "small-model"
    assert kwargs["messages"][0] == {
        "role": "system",
        "content": show_people.CLASSIFIER_INSTRUCTION,
    }
    assert kwargs["messages"][1]["content"] == (
        "Begriff: Beratung\nBeruf: Bank\nLerneinheit: Kunden"
    )
    assert kwargs["response_format"] == show_people.CLASSIFIER_RESPONSE_FORMAT


def test_classifier_input_leaves_out_missing_context() -> None:
    context = ImagePromptContext(word="Hammer", unit_title=None, job_title=None)

    assert show_people.classifier_input(context) == "Begriff: Hammer"


@pytest.mark.parametrize(
    "content", ["", "ja", "{}", '{"show_people": "yes"}', "[true]"]
)
def test_classify_rejects_unexpected_answers(content: str) -> None:
    client = classifier_answer(content)
    with (
        mock.patch.object(show_people, "get_openai_client", return_value=client),
        pytest.raises(ValueError),
    ):
        show_people.classify_show_people(CONTEXT)


@pytest.mark.django_db
def test_a_prompt_without_variants_never_classifies(
    classifier: mock.MagicMock,
) -> None:
    word = Word.objects.create(word="Beratung", singular_article=2)

    decision = show_people.resolve_show_people(word, ImagePrompt.get_default(), CONTEXT)

    assert decision is False
    classifier.chat.completions.create.assert_not_called()
    word.refresh_from_db()
    assert word.show_people is None


@pytest.mark.django_db
def test_an_undecided_word_is_classified_once_and_the_result_stored(
    classifier: mock.MagicMock,
) -> None:
    prompt = people_prompt()
    word = Word.objects.create(word="Beratung", singular_article=2)

    assert show_people.resolve_show_people(word, prompt, CONTEXT) is True
    assert show_people.resolve_show_people(word, prompt, CONTEXT) is True

    assert classifier.chat.completions.create.call_count == 1
    word.refresh_from_db()
    assert word.show_people is True
    assert not word.show_people_overridden


@pytest.mark.django_db
def test_a_stored_decision_is_used_without_classifying(
    classifier: mock.MagicMock,
) -> None:
    word = Word.objects.create(word="Beratung", singular_article=2)
    Word.objects.filter(pk=word.pk).update(show_people=False)
    word.refresh_from_db()

    assert show_people.resolve_show_people(word, people_prompt(), CONTEXT) is False
    classifier.chat.completions.create.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "error",
    [OpenAIConfigurationError("no key"), OpenAIError("down"), ValueError("bad")],
)
def test_a_failed_classification_falls_back_to_no_people_and_stores_nothing(
    error: Exception,
) -> None:
    word = Word.objects.create(word="Beratung", singular_article=2)

    with mock.patch.object(show_people, "classify_show_people", side_effect=error):
        decision = show_people.resolve_show_people(word, people_prompt(), CONTEXT)

    assert decision is False
    word.refresh_from_db()
    assert word.show_people is None


@pytest.mark.django_db
def test_an_editor_decision_is_marked_as_overridden() -> None:
    word = Word.objects.create(word="Beratung", singular_article=2)
    Word.objects.filter(pk=word.pk).update(show_people=True)
    word.refresh_from_db()

    show_people.set_show_people(word, False)

    word.refresh_from_db()
    assert word.show_people is False
    assert word.show_people_overridden


@pytest.mark.django_db
def test_confirming_the_stored_decision_does_not_override_it() -> None:
    word = Word.objects.create(word="Beratung", singular_article=2)
    Word.objects.filter(pk=word.pk).update(show_people=True)
    word.refresh_from_db()

    show_people.set_show_people(word, True)

    word.refresh_from_db()
    assert not word.show_people_overridden


@pytest.mark.django_db
def test_the_word_prompt_uses_the_variant_of_the_classified_decision(
    classifier: mock.MagicMock,
) -> None:
    prompt = people_prompt()
    word = Word.objects.create(word="Beratung", singular_article=2)

    assert build_word_image_prompt(word, image_prompt=prompt).startswith("MIT Beratung")
    assert build_word_image_prompt(
        word, image_prompt=prompt, show_people=False
    ).startswith("OHNE Beratung")


@pytest.mark.django_db
def test_the_classifier_gets_the_context_of_the_image_prompt(
    classifier: mock.MagicMock,
) -> None:
    job = Job.objects.create(name="Bank")
    unit = Unit.objects.create(title="Kunden")
    unit.jobs.add(job)
    word = Word.objects.create(word="Beratung", singular_article=2)
    UnitWordRelation.objects.create(unit=unit, word=word)

    build_word_image_prompt(word, image_prompt=people_prompt())

    message = classifier.chat.completions.create.call_args.kwargs["messages"][1]
    assert message["content"] == show_people.classifier_input(
        image_prompt_context(word)
    )
    assert "Beruf: Bank" in message["content"]
