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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Area, Job, Word

# Imported via ``import_module`` so the patch targets the module, whatever
# ``lunes_cms.cmsv2.views`` re-exports under the same name.
import_csv_view = import_module("lunes_cms.cmsv2.views.import_csv_view")


@pytest.fixture(autouse=True)
def _no_asset_generation() -> Generator[mock.Mock, None, None]:
    """
    A successful import starts a thread that generates the assets of the new
    words. With its own database connection it would run into the lock the
    transaction of the test holds, so it is stubbed out here.
    """
    with mock.patch.object(import_csv_view, "_generate_word_assets") as generate:
        yield generate


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
        {"job": job.pk, "csv_file": non_utf8_csv},
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
def test_asset_generation_is_recorded_for_the_areas_of_the_importing_user(
    client: Client,
) -> None:
    areas = [Area.objects.create(name="Kolping"), Area.objects.create(name="Caritas")]
    job = Job.objects.create(name="Tischler", area=areas[0])
    user = get_user_model().objects.create_user(username="kolping", is_staff=True)
    user.user_permissions.add(
        *Permission.objects.filter(codename__in=["add_word", "add_unit"])
    )
    # Words imported by non-superusers are credited to the group of the user.
    user.groups.add(Group.objects.create(name="Kolping"))
    for area in areas:
        area.admins.add(user)
    client.force_login(user)

    with mock.patch.object(import_csv_view.threading, "Thread") as thread:
        _import_tool(client, job, "Hammer", "der")

    _word_ids, _job_title, thread_areas = thread.call_args.kwargs["args"]
    assert set(thread_areas) == set(areas)
