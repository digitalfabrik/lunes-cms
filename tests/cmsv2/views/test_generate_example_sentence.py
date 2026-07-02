"""
Tests for the example sentence generation AJAX endpoints.
"""

from __future__ import annotations

from unittest import mock

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.unit import Unit, UnitWordRelation
from lunes_cms.cmsv2.utils import OpenAIConfigurationError
from lunes_cms.cmsv2.views import generate_example_sentence

WordWithJob = tuple[Word, Job, Unit, UnitWordRelation]


@pytest.fixture
def word_with_job(db: None) -> WordWithJob:
    word = Word.objects.create(word="Hammer", singular_article=1)
    job = Job.objects.create(name="Tischler")
    unit = Unit.objects.create(title="Werkzeuge")
    unit.jobs.add(job)
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    return word, job, unit, relation


def test_word_endpoint_returns_generated_sentence(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence,
        "openai_example_sentence",
        return_value="Der Hammer liegt auf der Werkbank.",
    ) as generate:
        response = admin_client.post(url)

    assert response.status_code == 200
    assert response.json()["example_sentence"] == "Der Hammer liegt auf der Werkbank."
    generate.assert_called_once_with("Hammer", "Tischler", None)


def test_word_endpoint_joins_multiple_jobs(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    other_job = Job.objects.create(name="Maler")
    other_unit = Unit.objects.create(title="Farben")
    other_unit.jobs.add(other_job)
    UnitWordRelation.objects.create(unit=other_unit, word=word)
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence,
        "openai_example_sentence",
        return_value="Satz.",
    ) as generate:
        response = admin_client.post(url)

    assert response.status_code == 200
    generate.assert_called_once_with("Hammer", "Maler, Tischler", None)


def test_word_endpoint_requires_job(admin_client: Client, db: None) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence, "openai_example_sentence"
    ) as generate:
        response = admin_client.post(url)

    assert response.status_code == 400
    assert "error" in response.json()
    generate.assert_not_called()


def test_unitword_endpoint_passes_unit_title(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    _word, _job, _unit, relation = word_with_job
    url = reverse(
        "cmsv2:unitword_generate_example_sentence_via_openai", args=[relation.pk]
    )

    with mock.patch.object(
        generate_example_sentence,
        "openai_example_sentence",
        return_value="Der Hammer liegt auf der Werkbank.",
    ) as generate:
        response = admin_client.post(url)

    assert response.status_code == 200
    generate.assert_called_once_with("Hammer", "Tischler", "Werkzeuge")


def test_endpoint_reports_missing_openai_configuration(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence,
        "openai_example_sentence",
        side_effect=OpenAIConfigurationError("missing key"),
    ):
        response = admin_client.post(url)

    assert response.status_code == 503
    assert response.json()["error"] == "missing key"


def test_endpoint_reports_generation_errors(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence,
        "openai_example_sentence",
        side_effect=ValueError("boom"),
    ):
        response = admin_client.post(url)

    assert response.status_code == 500
    assert response.json()["error"] == "boom"


def test_endpoints_require_post(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, relation = word_with_job
    for url in [
        reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk]),
        reverse(
            "cmsv2:unitword_generate_example_sentence_via_openai", args=[relation.pk]
        ),
        reverse("cmsv2:word_store_generated_example_sentence", args=[word.pk]),
        reverse("cmsv2:unitword_store_generated_example_sentence", args=[relation.pk]),
    ]:
        assert admin_client.get(url).status_code == 405


def test_word_store_persists_kept_sentence(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    url = reverse("cmsv2:word_store_generated_example_sentence", args=[word.pk])

    response = admin_client.post(
        url,
        {"example_sentence": "Der Hammer liegt auf der Werkbank."},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    word.refresh_from_db()
    assert word.example_sentence == "Der Hammer liegt auf der Werkbank."


def test_word_store_resets_check_status_and_audio(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    from django.core.files.base import ContentFile

    word, _job, _unit, _relation = word_with_job
    word.example_sentence = "Alter Satz."
    word.example_sentence_check_status = "CONFIRMED"
    word.example_sentence_audio.save("old.mp3", ContentFile(b"audio"), save=False)
    word.save()

    url = reverse("cmsv2:word_store_generated_example_sentence", args=[word.pk])
    admin_client.post(
        url,
        {"example_sentence": "Neuer Satz."},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    word.refresh_from_db()
    assert word.example_sentence == "Neuer Satz."
    # Changing the sentence resets the check status and drops the stale audio.
    assert word.example_sentence_check_status == "NOT_CHECKED"
    assert not word.example_sentence_audio


def test_word_store_requires_sentence(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    word, _job, _unit, _relation = word_with_job
    url = reverse("cmsv2:word_store_generated_example_sentence", args=[word.pk])

    response = admin_client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_unitword_store_persists_kept_sentence(
    admin_client: Client, word_with_job: WordWithJob
) -> None:
    _word, _job, _unit, relation = word_with_job
    url = reverse("cmsv2:unitword_store_generated_example_sentence", args=[relation.pk])

    response = admin_client.post(
        url,
        {"example_sentence": "Im Werkzeugkasten liegt ein Hammer."},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    relation.refresh_from_db()
    assert relation.example_sentence == "Im Werkzeugkasten liegt ein Hammer."


def test_example_sentence_widget_renders_keep_discard(db: None) -> None:
    from django.contrib import admin as django_admin

    from lunes_cms.cmsv2.admins.word_admin import WordAdmin

    word = Word.objects.create(word="Hammer", singular_article=1)
    word_admin = WordAdmin(Word, django_admin.site)

    html = str(word_admin.example_sentence_generate(word))
    assert "generate-example-sentence-keep-btn" in html
    assert "generate-example-sentence-discard-btn" in html
    assert 'data-target="id_example_sentence"' in html
    assert (
        reverse("cmsv2:word_store_generated_example_sentence", args=[word.pk]) in html
    )
