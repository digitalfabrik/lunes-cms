"""
Tests for the area behaviour of the admin: which content a user sees, who may
assign an area, and the guards on the job actions.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import Client, RequestFactory

from lunes_cms.cmsv2.admins.area_admin import AreaAdmin
from lunes_cms.cmsv2.admins.job_admin import JobAdmin
from lunes_cms.cmsv2.admins.unit_admin import UnitAdmin, UnitAdminForm
from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Area, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def job_admin() -> JobAdmin:
    return JobAdmin(Job, admin.site)


@pytest.fixture
def area(db: None) -> Area:
    return Area.objects.create(name="Kolping")


def _user(username: str, **kwargs: Any) -> User:
    """Create a user in a group, as ``BaseAdmin.save_model()`` expects."""
    user = get_user_model().objects.create_user(username=username, **kwargs)
    user.groups.add(Group.objects.get_or_create(name="Content managers")[0])
    return user


def _get_request(request_factory: RequestFactory, user: User) -> HttpRequest:
    request = request_factory.get("/")
    request.user = user
    return request


def _post_request(request_factory: RequestFactory, user: User) -> HttpRequest:
    request = request_factory.post("/")
    request.user = user
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


def test_job_admin_queryset_is_scoped_to_the_area(
    area: Area, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """An area administrator only sees the jobs of their own area."""
    area_job = Job.objects.create(name="Area job", area=area)
    main_job = Job.objects.create(name="Main job")
    admin_user = _user("area-admin")
    area.admins.add(admin_user)

    visible = job_admin.get_queryset(_get_request(request_factory, admin_user))

    assert set(visible) == {area_job}
    plain_visible = set(
        job_admin.get_queryset(_get_request(request_factory, _user("plain")))
    )
    assert main_job in plain_visible
    assert area_job not in plain_visible


def test_unit_and_word_admin_querysets_are_scoped_to_the_area(
    area: Area, request_factory: RequestFactory
) -> None:
    """The same scoping applies to units and words."""
    area_unit = Unit.objects.create(title="Area unit")
    area_unit.jobs.add(Job.objects.create(name="Area job", area=area))
    main_unit = Unit.objects.create(title="Main unit")
    main_unit.jobs.add(Job.objects.create(name="Main job"))
    # Only the area content is asserted exactly, the database may hold
    # fixture content of the main app as well.
    area_word = Word.objects.create(word="Bereichswort", singular_article=1)
    main_word = Word.objects.create(word="Hauptwort", singular_article=1)
    UnitWordRelation.objects.create(unit=area_unit, word=area_word)
    UnitWordRelation.objects.create(unit=main_unit, word=main_word)

    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    request = _get_request(request_factory, admin_user)

    assert set(UnitAdmin(Unit, admin.site).get_queryset(request)) == {area_unit}
    assert set(WordAdmin(Word, admin.site).get_queryset(request)) == {area_word}


def test_save_model_assigns_the_area_of_the_creator(
    area: Area, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """A job created by an area administrator lands in their area."""
    admin_user = _user("area-admin")
    area.admins.add(admin_user)
    job = Job(name="New job")

    job_admin.save_model(
        _post_request(request_factory, admin_user), job, form=None, change=False  # type: ignore[arg-type]
    )

    job.refresh_from_db()
    assert job.area == area


def test_save_model_leaves_jobs_of_other_users_without_an_area(
    db: None, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """A content manager without an area keeps creating main app jobs."""
    plain_user = _user("plain")
    job = Job(name="New job")

    job_admin.save_model(
        _post_request(request_factory, plain_user), job, form=None, change=False  # type: ignore[arg-type]
    )

    job.refresh_from_db()
    assert job.area is None


def test_area_field_is_read_only_for_area_admins(
    area: Area, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """
    Only superusers move a job between areas. An administrator of several
    areas still has to pick one on the add form.
    """
    single_area_admin = _user("single")
    area.admins.add(single_area_admin)
    second_area = Area.objects.create(name="Second")
    multi_area_admin = _user("multi")
    area.admins.add(multi_area_admin)
    second_area.admins.add(multi_area_admin)
    superuser = _user("root", is_superuser=True)

    single_request = _get_request(request_factory, single_area_admin)
    assert "area" in job_admin.get_readonly_fields(single_request)

    multi_request = _get_request(request_factory, multi_area_admin)
    assert "area" not in job_admin.get_readonly_fields(multi_request)
    job = Job.objects.create(name="Job", area=area)
    assert "area" in job_admin.get_readonly_fields(multi_request, job)

    assert "area" not in job_admin.get_readonly_fields(
        _get_request(request_factory, superuser)
    )


def test_duplicate_jobs_skips_jobs_of_an_area(
    area: Area, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """
    Duplicating a job of an area would share its units with a second job, so
    those jobs are skipped.
    """
    Job.objects.create(name="Area job", area=area)
    Job.objects.create(name="Main job")

    job_admin.duplicate_jobs(
        _post_request(request_factory, _user("root", is_superuser=True)),
        Job.objects.filter(name__in=["Area job", "Main job"]),
    )

    assert Job.objects.filter(name__startswith="Area job").count() == 1
    assert Job.objects.filter(name__startswith="Main job").count() == 2


def test_unit_admin_form_rejects_mixing_areas(area: Area) -> None:
    """The unit form refuses to assign a unit of an area to a second job."""
    area_job = Job.objects.create(name="Area job", area=area)
    main_job = Job.objects.create(name="Main job")
    unit = Unit.objects.create(title="Unit")
    unit.jobs.add(area_job)

    form = UnitAdminForm(
        data={"title": "Unit", "jobs": [area_job.pk, main_job.pk]}, instance=unit
    )

    assert not form.is_valid()
    assert "jobs" in form.errors


def test_admin_change_lists_render_with_the_area_column(
    area: Area, client: Client
) -> None:
    """
    The area column of the job, unit and word list is derived, so render the
    lists once to make sure the admin configuration holds together.
    """
    superuser = get_user_model().objects.create_superuser(
        username="root-render", email="root@example.com", password="secret"
    )
    client.force_login(superuser)
    unit = Unit.objects.create(title="Area unit")
    unit.jobs.add(Job.objects.create(name="Area job", area=area))
    word = Word.objects.create(word="Bereichswort", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=word)

    for url in (
        "/en/admin/cmsv2/area/",
        "/en/admin/cmsv2/job/",
        "/en/admin/cmsv2/unit/",
        "/en/admin/cmsv2/word/",
    ):
        assert client.get(url).status_code == 200, url


def test_area_admin_is_restricted_to_superusers(
    db: None, request_factory: RequestFactory
) -> None:
    """Areas decide who sees what, so only superusers may manage them."""
    area_admin = AreaAdmin(Area, admin.site)
    plain_request = _get_request(request_factory, _user("plain"))
    superuser_request = _get_request(
        request_factory, _user("root", is_superuser=True)
    )

    assert area_admin.has_module_permission(plain_request) is False
    assert area_admin.has_view_permission(plain_request) is False
    assert area_admin.has_add_permission(plain_request) is False
    assert area_admin.has_change_permission(plain_request) is False
    assert area_admin.has_delete_permission(plain_request) is False
    assert area_admin.has_module_permission(superuser_request) is True
    assert area_admin.has_change_permission(superuser_request) is True
