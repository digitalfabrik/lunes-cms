"""
Tests for the example sentence generation AJAX endpoints.
"""

from unittest import mock

import pytest
from django.urls import reverse

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.unit import Unit, UnitWordRelation
from lunes_cms.cmsv2.utils import OpenAIConfigurationError
from lunes_cms.cmsv2.views import generate_example_sentence


@pytest.fixture
def word_with_job(db):
    word = Word.objects.create(word="Hammer", singular_article=1)
    job = Job.objects.create(name="Tischler")
    unit = Unit.objects.create(title="Werkzeuge")
    unit.jobs.add(job)
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    return word, job, unit, relation


def test_word_endpoint_returns_generated_sentence(admin_client, word_with_job):
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


def test_word_endpoint_joins_multiple_jobs(admin_client, word_with_job):
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


def test_word_endpoint_requires_job(admin_client, db):
    word = Word.objects.create(word="Hammer", singular_article=1)
    url = reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk])

    with mock.patch.object(
        generate_example_sentence, "openai_example_sentence"
    ) as generate:
        response = admin_client.post(url)

    assert response.status_code == 400
    assert "error" in response.json()
    generate.assert_not_called()


def test_unitword_endpoint_passes_unit_title(admin_client, word_with_job):
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


def test_endpoint_reports_missing_openai_configuration(admin_client, word_with_job):
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


def test_endpoint_reports_generation_errors(admin_client, word_with_job):
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


def test_endpoints_require_post(admin_client, word_with_job):
    word, _job, _unit, relation = word_with_job
    for url in [
        reverse("cmsv2:word_generate_example_sentence_via_openai", args=[word.pk]),
        reverse(
            "cmsv2:unitword_generate_example_sentence_via_openai", args=[relation.pk]
        ),
    ]:
        assert admin_client.get(url).status_code == 405
