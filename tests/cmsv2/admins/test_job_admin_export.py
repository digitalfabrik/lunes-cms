"""
Tests for the "Export all vocabulary for these jobs to CSV" admin action
(issue #738) — specifically that the exported "Units" column only lists
units of the job being exported, not units of unrelated jobs.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from django.contrib import admin
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import RequestFactory

from lunes_cms.cmsv2.admins.job_admin import JobAdmin
from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def job_admin() -> JobAdmin:
    return JobAdmin(Job, admin.site)


def _post_request(request_factory: RequestFactory) -> HttpRequest:
    request = request_factory.post("/")
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


@pytest.mark.django_db()
def test_export_to_csv_only_lists_units_of_the_exported_job(
    job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    job_a = Job.objects.create(name="Bäcker/-in")
    job_b = Job.objects.create(name="Kfz-Mechatroniker/-in")
    unit_a = Unit.objects.create(title="Backofen")
    unit_a.jobs.add(job_a)
    unit_b = Unit.objects.create(title="Bremsen")
    unit_b.jobs.add(job_b)
    word = Word.objects.create(word="Schraubenzieher", singular_article=1)
    UnitWordRelation.objects.create(unit=unit_a, word=word)
    UnitWordRelation.objects.create(unit=unit_b, word=word)

    request = _post_request(request_factory)
    response = job_admin.export_to_csv(request, Job.objects.filter(pk=job_a.pk))

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        csv_content = archive.read(archive.namelist()[0]).decode()

    assert "Backofen" in csv_content
    assert "Bremsen" not in csv_content
