"""
Tests for the CSV import view's up-front validation: an empty file must
notify the user that nothing was imported, and a file with the wrong header
structure must be rejected with a clear format error, before any row-level
processing happens.
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Job, Word


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
        {"job": job.pk, "csv_file": _upload("Einheit,Vokabel,Artikel\n")},
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
def test_valid_file_still_imports_successfully(admin_client: Client, job: Job) -> None:
    response = admin_client.post(
        reverse("cmsv2:import_csv"),
        {
            "job": job.pk,
            "csv_file": _upload("Einheit,Vokabel,Artikel\nWerkzeug,Hammer,der\n"),
        },
        follow=True,
    )

    messages = [str(m) for m in response.context["messages"]]
    assert any("import successful" in m.lower() for m in messages)
    assert Word.objects.filter(units__jobs=job, word="Hammer").exists()
