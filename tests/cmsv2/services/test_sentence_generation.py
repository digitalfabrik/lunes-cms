"""
Tests for example sentence generation via OpenAI.
"""

from unittest import mock

import pytest
from django.conf import settings

from lunes_cms.cmsv2.services import sentence_generation


def _fake_openai_client(content="Der Hammer liegt auf der Werkbank."):
    fake_message = mock.Mock()
    fake_message.content = content
    fake_choice = mock.Mock()
    fake_choice.message = fake_message
    fake_response = mock.Mock()
    fake_response.choices = [fake_choice]
    fake_client = mock.Mock()
    fake_client.chat.completions.create.return_value = fake_response
    return fake_client


def test_prompt_contains_word_and_job():
    prompt = sentence_generation.build_example_sentence_prompt("Hammer", "Tischler")
    assert "Fachbegriff Hammer" in prompt
    assert "im Rahmen des Berufs Tischler" in prompt
    assert "Lerneinheit" not in prompt
    assert "B1" in prompt
    assert "5-10 Wörter" in prompt


def test_prompt_contains_unit_when_given():
    prompt = sentence_generation.build_example_sentence_prompt(
        "Hammer", "Tischler", "Werkzeuge"
    )
    assert "im Rahmen des Berufs Tischler und der Lerneinheit Werkzeuge" in prompt


def test_generation_uses_text_model_and_returns_sentence():
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
def test_generation_strips_quotes_and_whitespace(raw, expected):
    fake_client = _fake_openai_client(content=raw)

    with mock.patch.object(
        sentence_generation, "get_openai_client", return_value=fake_client
    ):
        assert (
            sentence_generation.openai_example_sentence("Hammer", "Tischler")
            == expected
        )


@pytest.mark.parametrize("content", [None, "", '""'])
def test_generation_raises_on_empty_response(content):
    fake_client = _fake_openai_client(content=content)

    with mock.patch.object(
        sentence_generation, "get_openai_client", return_value=fake_client
    ):
        with pytest.raises(ValueError):
            sentence_generation.openai_example_sentence("Hammer", "Tischler")
