from __future__ import annotations

from collections.abc import Generator
from importlib import import_module
from unittest import mock

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.unit import Unit, UnitWordRelation

# ``lunes_cms.cmsv2.views`` re-exports a *function* of this exact name, which
# shadows the submodule — a plain import would yield the function, which is not
# a patchable target. The other two view modules are not shadowed.
unitword_view = import_module(
    "lunes_cms.cmsv2.views.unitword_generate_example_sentence_audio"
)

SENTENCE = "Ich backe ein Baiser."


@pytest.fixture
def word(db: None) -> Word:
    return Word.objects.create(
        word="Baiser",
        singular_article=3,
        pronunciation="Bessee",
        example_sentence=SENTENCE,
    )


@pytest.fixture
def relation(word: Word) -> UnitWordRelation:
    job = Job.objects.create(name="Bäcker/-in")
    unit = Unit.objects.create(title="Backwaren")
    unit.jobs.add(job)
    return UnitWordRelation.objects.create(
        unit=unit, word=word, example_sentence="Das Baiser ist fertig."
    )


def test_word_widget_passes_pronunciation(admin_client: Client, word: Word) -> None:
    url = reverse(
        "cmsv2:word_generate_example_sentence_audio_via_openai", args=[word.pk]
    )

    with mock.patch(
        "lunes_cms.cmsv2.views.word_generate_example_sentence_audio"
        ".openai_sentence_audio_bytes",
        return_value=b"mp3",
    ) as generate:
        response = admin_client.post(url, {"example_sentence_text": SENTENCE})

    assert response.status_code == 200
    generate.assert_called_once_with(SENTENCE, word)


def test_unitword_page_passes_pronunciation_of_its_word(
    admin_client: Client, relation: UnitWordRelation
) -> None:
    url = reverse(
        "cmsv2:unitword_generate_example_sentence_audio_via_openai",
        args=[relation.pk],
    )

    with mock.patch.object(
        unitword_view, "openai_sentence_audio_bytes", return_value=b"mp3"
    ) as generate:
        response = admin_client.post(
            url, {"example_sentence_text": "Das Baiser ist fertig."}
        )

    assert response.status_code == 200
    generate.assert_called_once_with("Das Baiser ist fertig.", relation.word)


def test_word_audio_uses_the_stored_variant_not_the_posted_text(
    admin_client: Client, word: Word
) -> None:
    url = reverse("cmsv2:word_generate_audio_via_openai", args=[word.pk])

    with mock.patch(
        "lunes_cms.cmsv2.views.word_generate_audio.openai_word_audio_bytes",
        return_value=b"mp3",
    ) as generate:
        response = admin_client.post(url, {"word_text": "das Baiser"})

    assert response.status_code == 200
    generate.assert_called_once_with("das Bessee")


def test_word_widget_rejects_unknown_word(admin_client: Client, db: None) -> None:
    url = reverse("cmsv2:word_generate_example_sentence_audio_via_openai", args=[9999])

    response = admin_client.post(url, {"example_sentence_text": SENTENCE})

    assert response.status_code == 404


@pytest.mark.django_db()
def test_regenerate_command_passes_pronunciation(word: Word) -> None:
    word.example_sentence_audio.save(
        "baiser_example_sentence.mp3", ContentFile(b"old"), save=True
    )

    with mock.patch(
        "lunes_cms.cmsv2.management.commands.regenerate_example_sentence_audio"
        ".openai_sentence_audio_bytes",
        return_value=b"new",
    ) as generate:
        call_command("regenerate_example_sentence_audio", limit=1)

    assert generate.call_args.args == (SENTENCE, word)
    word.refresh_from_db()
    assert word.example_sentence_audio.read() == b"new"
