"""
Tests for the CSV import view's up-front validation: an empty file must
notify the user that nothing was imported, and a file with the wrong header
structure must be rejected with a clear format error, before any row-level
processing happens.
"""

from __future__ import annotations

from collections.abc import Generator
from importlib import import_module
from typing import Any
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from pytest_django import Settings

from lunes_cms.cmsv2.models import ImagePrompt, Job, Word
from lunes_cms.cmsv2.services.image_generation import default_image_model

# Imported via ``import_module`` so the patch targets the module, whatever
# ``lunes_cms.cmsv2.views`` re-exports under the same name.
import_csv_view = import_module("lunes_cms.cmsv2.views.import_csv_view")
_generate_word_assets = import_csv_view._generate_word_assets


@pytest.fixture(autouse=True)
def _no_asset_generation() -> Generator[mock.Mock, None, None]:
    """
    A successful import starts a thread that generates the assets of the new
    words. With its own database connection it would run into the lock the
    transaction of the test holds, so it is stubbed out here.
    """
    with mock.patch.object(import_csv_view, "_generate_word_assets") as generate:
        yield generate


def _image_selection() -> dict[str, Any]:
    """
    The image model and prompt the import form preselects.
    """
    return {
        "image_model": default_image_model(),
        "image_prompt": ImagePrompt.get_default().pk,
    }


def _upload(content: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "vocabulary.csv", content.encode("utf-8"), content_type="text/csv"
    )


@pytest.fixture
def job(db: None) -> Job:
    return Job.objects.create(name="Test Job")


@pytest.mark.django_db()
def test_header_only_file_reports_no_entries(admin_client: Client, job: Job) -> None:
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            **_image_selection(),
            "csv_file": _upload("Einheit,Vokabel,Artikel\n"),
        },
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    assert any("no entries" in m.lower() for m in messages)
    assert not Word.objects.filter(units__jobs=job).exists()


@pytest.mark.django_db()
def test_wrong_header_structure_is_rejected_before_any_row_processing(
    admin_client: Client, job: Job
) -> None:
    """A file whose headers don't match the expected structure at all must
    be rejected up front with a format error, not processed row by row."""
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            **_image_selection(),
            "csv_file": _upload(
                "this is not a csv file at all\njust some random text\n"
            ),
        },
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    assert any("not in the correct format" in m.lower() for m in messages)
    assert not Word.objects.filter(units__jobs=job).exists()


@pytest.mark.django_db()
def test_non_utf8_file_shows_friendly_encoding_error(
    admin_client: Client, job: Job
) -> None:
    """A CSV file that isn't UTF-8 encoded must show a friendly message
    telling the user to save it as UTF-8, not the raw Python decoding
    error."""
    non_utf8_csv = SimpleUploadedFile(
        "vocabulary.csv",
        "Einheit,Vokabel,Artikel\nWerkzeug,Hämmer,der\n".encode("latin-1"),
        content_type="text/csv",
    )
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {"job": job.pk, **_image_selection(), "csv_file": non_utf8_csv},
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    assert any("utf-8" in m.lower() for m in messages)
    assert not any("codec can't decode" in m.lower() for m in messages)
    assert not Word.objects.filter(units__jobs=job).exists()


@pytest.mark.django_db()
def test_valid_file_still_imports_successfully(admin_client: Client, job: Job) -> None:
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            **_image_selection(),
            "csv_file": _upload("Einheit,Vokabel,Artikel\nWerkzeug,Hammer,der\n"),
        },
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    assert any("import successful" in m.lower() for m in messages)
    assert Word.objects.filter(units__jobs=job, word="Hammer").exists()


@pytest.mark.django_db()
def test_success_message_counts_only_data_rows(admin_client: Client, job: Job) -> None:
    """The success message must report exactly the imported data rows:
    neither the header row nor the created units may be counted as words,
    and there is no "updated" count since the import never updates
    existing records (issues #761 and #907)."""
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            **_image_selection(),
            "csv_file": _upload(
                "Einheit,Vokabel,Artikel\n"
                "Werkzeug,Hammer,der\n"
                "Werkzeug,Säge,die\n"
                "Werkzeug,Zange,die\n"
                "Werkzeug,Bohrer,der\n"
            ),
        },
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    success = next(m for m in messages if "import successful" in m.lower())
    assert "4 new words" in success
    assert "1 new unit" in success
    assert "updated" not in success.lower()
    assert Word.objects.filter(units__jobs=job).distinct().count() == 4


def _import_tool(admin_client: Client, job: Job, word: str, article: str) -> Any:
    return admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            **_image_selection(),
            "csv_file": _upload(
                f"Einheit,Vokabel,Artikel\nWerkzeug,{word},{article}\n"
            ),
        },
        follow=True,
    )


@pytest.mark.django_db()
def test_second_import_reports_the_extended_unit(
    admin_client: Client, job: Job
) -> None:
    """The message tells the user that the second CSV extended the unit that
    was already there rather than adding another one."""
    _import_tool(admin_client, job, "Hammer", "der")

    response = _import_tool(admin_client, job, "Säge", "die")

    messages = [str(m) for m in response.context["messages"]]
    assert any("existing unit was extended" in m for m in messages)


@pytest.mark.django_db()
def test_form_explains_the_image_prompt_with_the_job(
    admin_client: Client, job: Job
) -> None:
    response = admin_client.get(reverse("cmsv2:import_csv_for_job", args=[job.pk]))

    content = response.content.decode()
    assert 'class="image-prompt-info"' in content
    assert "Beruflicher Kontext: Test Job." in content


@pytest.fixture
def two_models(settings: Settings) -> None:
    settings.OPENAI_IMAGE_MODELS = ["model-a", "model-b"]


@pytest.mark.django_db()
def test_form_preselects_the_default_model_and_prompt(
    admin_client: Client, job: Job, two_models: None
) -> None:
    ImagePrompt.objects.create(name="Inaktiv", prompt="I {{ word }}", is_active=False)

    response = admin_client.get(reverse("cmsv2:import_csv_for_job", args=[job.pk]))

    form = response.context["form"]
    assert form["image_model"].value() == "model-a"
    assert form["image_prompt"].value() == ImagePrompt.get_default().pk
    assert list(form.fields["image_prompt"].queryset) == [ImagePrompt.get_default()]
    content = response.content.decode()
    assert 'class="prompt-image-model"' in content
    assert reverse("cmsv2:import_image_prompt_preview_for_job", args=[job.pk]) in (
        content
    )
    assert "(default)" in content
    assert "Additional info" not in content


@pytest.mark.django_db()
def test_import_generates_images_with_the_selected_model_and_prompt(
    admin_client: Client,
    job: Job,
    two_models: None,
    _no_asset_generation: mock.Mock,
) -> None:
    selected = ImagePrompt.objects.create(name="Gewählt", prompt="G {{ word }}")

    admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            "image_model": "model-b",
            "image_prompt": selected.pk,
            "csv_file": _upload("Einheit,Vokabel,Artikel\nWerkzeug,Hammer,der\n"),
        },
    )

    _word_ids, generated_job, image_prompt, image_model = (
        _no_asset_generation.call_args.args
    )
    assert generated_job == job
    assert image_prompt == selected
    assert image_model == "model-b"


@pytest.mark.django_db()
@pytest.mark.parametrize(
    "selection", [{"image_model": "unknown-model"}, {"inactive_prompt": True}]
)
def test_import_rejects_an_unavailable_selection(
    admin_client: Client, job: Job, selection: dict[str, Any]
) -> None:
    data = {
        "job": job.pk,
        **_image_selection(),
        "csv_file": _upload("Einheit,Vokabel,Artikel\nWerkzeug,Hammer,der\n"),
    }
    if selection.pop("inactive_prompt", False):
        data["image_prompt"] = ImagePrompt.objects.create(
            name="Inaktiv", prompt="I {{ word }}", is_active=False
        ).pk
    data.update(selection)

    response = admin_client.post(reverse("cmsv2:import_csv"), data)

    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Word.objects.filter(units__jobs=job).exists()


@pytest.mark.django_db()
def test_generate_word_assets_passes_the_selection_to_the_image_drain() -> None:
    job = Job(name="Test Job")
    image_prompt = ImagePrompt(name="Gewählt")
    with (
        mock.patch.object(import_csv_view, "drain_pending_sentences"),
        mock.patch.object(import_csv_view, "drain_pending_audio"),
        mock.patch.object(import_csv_view, "drain_pending_images") as drain_images,
    ):
        _generate_word_assets([1, 2], job, image_prompt, "model-b")

    drain_images.assert_called_once_with(
        [1, 2], job=job, image_prompt=image_prompt, model="model-b"
    )


@pytest.mark.django_db()
def test_preview_follows_the_selected_prompt(admin_client: Client, job: Job) -> None:
    selected = ImagePrompt.objects.create(
        name="Mit Personen",
        supports_show_people=True,
        prompt_with_people="MIT {{ word }} {{ job }}",
        prompt_without_people="OHNE {{ word }} {{ job }}",
    )

    response = admin_client.post(
        reverse("cmsv2:import_image_prompt_preview_for_job", args=[job.pk]),
        {"image_prompt": selected.pk},
    )

    assert response.json()["prompt"].startswith("OHNE [word] Test Job")
    assert response.json()["supports_show_people"] is True


@pytest.mark.django_db()
def test_preview_without_a_job_uses_the_placeholder(admin_client: Client) -> None:
    response = admin_client.post(reverse("cmsv2:import_image_prompt_preview"))

    assert "[selected job]" in response.json()["prompt"]
    assert response.json()["supports_show_people"] is False


@pytest.mark.django_db()
def test_preview_rejects_an_inactive_prompt(admin_client: Client) -> None:
    inactive = ImagePrompt.objects.create(
        name="Inaktiv", prompt="I {{ word }}", is_active=False
    )

    response = admin_client.post(
        reverse("cmsv2:import_image_prompt_preview"), {"image_prompt": inactive.pk}
    )

    assert response.status_code == 400
