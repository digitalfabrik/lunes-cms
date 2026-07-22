"""
Tests for the archive/restore behaviour of the Job admin (issue #890).

Covers the ``archive_jobs``/``restore_jobs`` bulk actions, the default admin
list hiding archived jobs, and the ``ArchivedFilter`` that lets content managers
view archived jobs.
"""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import RequestFactory

from lunes_cms.cmsv2.admins.job_admin import ArchivedFilter, JobAdmin
from lunes_cms.cmsv2.models import Job


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def job_admin() -> JobAdmin:
    return JobAdmin(Job, admin.site)


def _post_request(request_factory: RequestFactory) -> HttpRequest:
    """Build a POST request with a working messages store for admin actions."""
    request = request_factory.post("/")
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


def test_archive_jobs_action_sets_archived_and_unpublishes(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    job = Job.objects.create(name="Bäcker/-in", released=True)

    request = _post_request(request_factory)

    job_admin.archive_jobs(request, Job.objects.filter(pk=job.pk))

    job.refresh_from_db()
    assert job.archived is True
    # An archived job must no longer be published (technical note in #890).
    assert job.released is False


def test_restore_jobs_action_clears_archived(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    job = Job.objects.create(name="Maurer/-in", archived=True)

    request = _post_request(request_factory)

    job_admin.restore_jobs(request, Job.objects.filter(pk=job.pk))

    job.refresh_from_db()
    assert job.archived is False


def test_duplicate_jobs_action_resets_archived(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """Duplicating an archived job produces an active (non-archived) copy."""
    job = Job.objects.create(name="Dachdecker/-in", archived=True)

    request = _post_request(request_factory)
    request.user = get_user_model().objects.create_user(username="editor")

    existing_pks = set(Job.objects.values_list("pk", flat=True))
    job_admin.duplicate_jobs(request, Job.objects.filter(pk=job.pk))

    duplicate = Job.objects.exclude(pk__in=existing_pks).get()
    assert duplicate.archived is False
    assert duplicate.released is False


def _apply_filter(
    request_factory: RequestFactory, job_admin: JobAdmin, params: dict[str, str]
) -> set[int]:
    """Run the ArchivedFilter against all jobs and return the matching pks."""
    request = request_factory.get("/", params)
    # Django's SimpleListFilter reads list-valued params (``value[-1]``).
    list_params = {key: [value] for key, value in params.items()}
    filter_instance = ArchivedFilter(request, list_params, Job, job_admin)
    queryset = filter_instance.queryset(request, Job.objects.all())
    return set(queryset.values_list("pk", flat=True))


def test_archived_filter_hides_archived_by_default(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    active = Job.objects.create(name="Active job")
    archived = Job.objects.create(name="Archived job", archived=True)

    pks = _apply_filter(request_factory, job_admin, {})

    assert active.pk in pks
    assert archived.pk not in pks


def test_archived_filter_shows_archived_when_selected(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    active = Job.objects.create(name="Active job")
    archived = Job.objects.create(name="Archived job", archived=True)

    pks = _apply_filter(request_factory, job_admin, {"archived": "archived"})

    assert archived.pk in pks
    assert active.pk not in pks


def test_archived_filter_all_shows_everything(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    active = Job.objects.create(name="Active job")
    archived = Job.objects.create(name="Archived job", archived=True)

    pks = _apply_filter(request_factory, job_admin, {"archived": "all"})

    assert {active.pk, archived.pk} <= pks


class _FakeChangeList:
    """Minimal changelist stub exposing only what SimpleListFilter.choices needs."""

    def get_query_string(
        self,
        new_params: dict[str, str] | None = None,
        remove: list[str] | None = None,
    ) -> str:
        return "?" + "&".join(f"{k}={v}" for k, v in (new_params or {}).items())


def test_archived_filter_default_choice_is_active(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    filter_instance = ArchivedFilter(request, {}, Job, job_admin)

    choices = list(filter_instance.choices(_FakeChangeList()))  # type: ignore[arg-type]
    # First choice is the "Active jobs" default and is selected when no filter set.
    assert str(choices[0]["display"]) == "Active jobs"
    assert choices[0]["selected"] is True
