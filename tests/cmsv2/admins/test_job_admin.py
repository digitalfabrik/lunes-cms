"""
Tests for the bulk actions and filters of the Job admin.

Covers the ``archive_jobs``/``restore_jobs`` bulk actions, the default admin
list hiding archived jobs, the ``ArchivedFilter`` that lets content managers
view archived jobs (issue #890), and the ``assign_to_user`` bulk action.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.test import RequestFactory

from lunes_cms.cmsv2.admins.job_admin import ArchivedFilter, JobAdmin
from lunes_cms.cmsv2.models import Area, Job, Review, Unit, UnitWordRelation, Word
from tests.cmsv2.helpers import PermissionClient


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def job_admin() -> JobAdmin:
    return JobAdmin(Job, admin.site)


def _post_request(
    request_factory: RequestFactory, data: dict | None = None
) -> HttpRequest:
    """Build a POST request with a working messages store for admin actions."""
    request = request_factory.post("/", data or {})
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


def test_duplicate_jobs_action_resets_status_flags(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """Duplicating a job produces an active, unreviewed copy."""
    job = Job.objects.create(name="Dachdecker/-in", archived=True, expert_reviewed=True)

    request = _post_request(request_factory)
    request.user = get_user_model().objects.create_user(username="editor")

    existing_pks = set(Job.objects.values_list("pk", flat=True))
    job_admin.duplicate_jobs(request, Job.objects.filter(pk=job.pk))

    duplicate = Job.objects.exclude(pk__in=existing_pks).get()
    assert duplicate.archived is False
    assert duplicate.released is False
    assert duplicate.expert_reviewed is False


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


#
# ``assign_to_user``: assigns every unit word of the units of the selected
# jobs to a reviewer. Requires the ``can_assign_reviews`` permission and is limited to
# the area of the user.
#


@pytest.fixture
def reviewer(db: None) -> User:
    return get_user_model().objects.create_user(username="reviewer")


@pytest.fixture
def admin_user(db: None) -> User:
    return get_user_model().objects.create_superuser(
        username="admin", password="password"
    )


def _unit_of_job(job: Job, title: str, *words: str) -> list[UnitWordRelation]:
    unit = Unit.objects.create(title=title)
    unit.jobs.add(job)
    return [
        UnitWordRelation.objects.create(
            unit=unit, word=Word.objects.create(word=word, singular_article=1)
        )
        for word in words
    ]


def _assign(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    jobs: list[Job],
    reviewer: User,
    admin_user: User,
) -> None:
    request = _post_request(request_factory, {"apply": "1", "user": reviewer.pk})
    request.user = admin_user
    job_admin.assign_to_user(request, Job.objects.filter(pk__in=[j.pk for j in jobs]))


def test_assign_to_user_reviews_every_unit_word_of_the_job(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    reviewer: User,
    admin_user: User,
) -> None:
    job = Job.objects.create(name="Maurer/-in")
    unit_words = _unit_of_job(job, "Unit A", "Hammer", "Kelle") + _unit_of_job(
        job, "Unit B", "Zange"
    )
    _unit_of_job(Job.objects.create(name="Bäcker/-in"), "Unit C", "Ofen")

    _assign(job_admin, request_factory, [job], reviewer, admin_user)

    reviews = Review.objects.filter(reviewer=reviewer)
    assert {review.unit_word for review in reviews} == set(unit_words)
    assert all(review.assigned_by == admin_user for review in reviews)


def test_assign_to_user_reviews_a_unit_shared_by_selected_jobs_once(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    reviewer: User,
    admin_user: User,
) -> None:
    job = Job.objects.create(name="Maurer/-in")
    other_job = Job.objects.create(name="Bäcker/-in")
    (unit_word,) = _unit_of_job(job, "Unit A", "Hammer")
    unit_word.unit.jobs.add(other_job)

    _assign(job_admin, request_factory, [job, other_job], reviewer, admin_user)

    assert Review.objects.filter(unit_word=unit_word, reviewer=reviewer).count() == 1


def test_assign_to_user_skips_already_assigned_unit_words(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    reviewer: User,
    admin_user: User,
) -> None:
    job = Job.objects.create(name="Maurer/-in")
    already_assigned, new = _unit_of_job(job, "Unit A", "Hammer", "Zange")
    Review.objects.create(unit_word=already_assigned, reviewer=reviewer)

    _assign(job_admin, request_factory, [job], reviewer, admin_user)

    assert Review.objects.filter(reviewer=reviewer).count() == 2
    assert Review.objects.filter(unit_word=new, reviewer=reviewer).exists()


def test_assign_to_user_asks_for_the_reviewer_first(
    job_admin: JobAdmin, request_factory: RequestFactory, admin_user: User
) -> None:
    job = Job.objects.create(name="Maurer/-in")
    _unit_of_job(job, "Unit A", "Hammer")

    request = _post_request(request_factory)
    request.user = admin_user

    response = job_admin.assign_to_user(request, Job.objects.filter(pk=job.pk))

    assert isinstance(response, TemplateResponse)
    assert response.template_name == "admin/cmsv2/assign_jobs_to_user.html"
    assert not Review.objects.exists()


def test_assign_to_user_is_hidden_from_an_anonymous_user(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    request.user = AnonymousUser()

    assert "assign_to_user" not in job_admin.get_actions(request)


def test_assign_to_user_is_hidden_from_a_non_superuser(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    request.user = get_user_model().objects.create_user(username="editor")

    assert "assign_to_user" not in job_admin.get_actions(request)


def test_assign_to_user_is_offered_to_a_superuser(
    job_admin: JobAdmin, request_factory: RequestFactory, admin_user: User
) -> None:
    request = request_factory.get("/")
    request.user = admin_user

    assert "assign_to_user" in job_admin.get_actions(request)


def test_assign_to_user_is_offered_to_a_user_who_may_assign(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    client_with_permissions: Callable[..., PermissionClient],
) -> None:
    request = request_factory.get("/")
    request.user = client_with_permissions("can_assign_reviews").user

    assert "assign_to_user" in job_admin.get_actions(request)


def test_assign_to_user_only_assigns_jobs_of_the_area_of_the_user(
    job_admin: JobAdmin,
    request_factory: RequestFactory,
    client_with_permissions: Callable[..., PermissionClient],
    reviewer: User,
    main_app_area: Area,
) -> None:
    other_area = Area.objects.create(name="Area B")
    own_job = Job.objects.create(name="Bäcker/-in", area=main_app_area)
    foreign_job = Job.objects.create(name="Koch/Köchin", area=other_area)
    own_unit = Unit.objects.create(title="Unit A", area=main_app_area)
    own_unit.jobs.add(own_job)
    foreign_unit = Unit.objects.create(title="Unit B", area=other_area)
    foreign_unit.jobs.add(foreign_job)
    own_unit_word = UnitWordRelation.objects.create(
        unit=own_unit,
        word=Word.objects.create(word="Ofen", singular_article=1, area=main_app_area),
    )
    UnitWordRelation.objects.create(
        unit=foreign_unit,
        word=Word.objects.create(word="Topf", singular_article=1, area=other_area),
    )

    request = _post_request(request_factory, {"apply": "1", "user": reviewer.pk})
    request.user = client_with_permissions("can_assign_reviews").user

    job_admin.assign_to_user(
        request, Job.objects.filter(pk__in=[own_job.pk, foreign_job.pk])
    )

    assert [review.unit_word for review in Review.objects.all()] == [own_unit_word]
