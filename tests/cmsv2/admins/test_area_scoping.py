"""
Tests for the area behaviour of the admin: which content a user sees, who may
assign an area, and the guards on the job actions.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import Client, RequestFactory

from lunes_cms.cmsv2.admins.area_admin import AreaAdmin
from lunes_cms.cmsv2.admins.job_admin import JobAdmin, JobAdminForm
from lunes_cms.cmsv2.admins.unit_admin import UnitAdmin, UnitAdminForm
from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Area, AreaCode, Job, Unit, Word
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


def test_codes_are_managed_on_the_area_page(area: Area, client: Client) -> None:
    """
    The codes of an area are added, changed and removed on its change page,
    and an invalid code is refused there.
    """
    superuser = get_user_model().objects.create_superuser(
        username="root-codes", email="root@example.com", password="secret"
    )
    client.force_login(superuser)
    url = f"/en/admin/cmsv2/area/{area.pk}/change/"
    form_data = {
        "name": area.name,
        "admins": [],
        "codes-TOTAL_FORMS": "1",
        "codes-INITIAL_FORMS": "0",
        "codes-MIN_NUM_FORMS": "0",
        "codes-MAX_NUM_FORMS": "1000",
        "codes-0-id": "",
        "codes-0-area": str(area.pk),
        "access_tokens-TOTAL_FORMS": "0",
        "access_tokens-INITIAL_FORMS": "0",
        "access_tokens-MIN_NUM_FORMS": "0",
        "access_tokens-MAX_NUM_FORMS": "0",
    }

    rejected = client.post(url, {**form_data, "codes-0-code": "short"})
    assert rejected.status_code == 200
    assert not AreaCode.objects.exists()

    accepted = client.post(url, {**form_data, "codes-0-code": "KOLPING1"})
    assert accepted.status_code == 302
    assert list(area.codes.values_list("code", flat=True)) == ["KOLPING1"]


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


def test_job_form_refuses_an_area_for_a_job_with_shared_units(area: Area) -> None:
    """
    Moving a job whose units are shared with other jobs into an area is
    refused, because its content would not belong to the area alone.
    """
    job = Job.objects.create(name="Job")
    unit = Unit.objects.create(title="Shared unit")
    unit.jobs.add(job, Job.objects.create(name="Other job"))

    form = JobAdminForm(data={"name": "Job", "area": area.pk}, instance=job)

    assert not form.is_valid()
    assert "area" in form.errors


def test_job_form_accepts_an_area_for_a_job_that_owns_its_units(area: Area) -> None:
    """A job whose units belong to it alone may be moved into an area."""
    job = Job.objects.create(name="Job")
    unit = Unit.objects.create(title="Own unit")
    unit.jobs.add(job)

    form = JobAdminForm(data={"name": "Job", "area": area.pk}, instance=job)

    assert form.is_valid(), form.errors


def test_area_is_preselected_and_required_for_area_admins(
    area: Area, job_admin: JobAdmin, request_factory: RequestFactory
) -> None:
    """
    An area administrator cannot leave the area of a new job empty, so no job
    of theirs ends up as main app content.
    """
    second_area = Area.objects.create(name="Second area")
    user = _user("multi")
    area.admins.add(user)
    second_area.admins.add(user)

    field = job_admin.formfield_for_foreignkey(
        Job._meta.get_field("area"), _get_request(request_factory, user)
    )

    assert field is not None and field.queryset is not None
    assert field.required is True
    assert field.initial in (area, second_area)
    assert list(field.queryset) == [area, second_area]


def test_area_admin_can_add_a_unit_with_a_word_of_the_own_area(
    area: Area, client: Client
) -> None:
    """
    Adding a unit of the own area together with a word that is already used in
    that area must work: the unit has no job in the database while the inline
    is validated, so the area comes from the jobs of the form.
    """
    admin_user = get_user_model().objects.create_superuser(
        username="root-add", email="root@example.com", password="secret"
    )
    client.force_login(admin_user)
    area_job = Job.objects.create(name="Area job", area=area)
    existing_unit = Unit.objects.create(title="Existing unit")
    existing_unit.jobs.add(area_job)
    word = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=existing_unit, word=word)

    response = client.post(
        "/en/admin/cmsv2/unit/add/",
        {
            "title": "New unit",
            "description": "",
            "jobs": [area_job.pk],
            "unit_word_relations-TOTAL_FORMS": "1",
            "unit_word_relations-INITIAL_FORMS": "0",
            "unit_word_relations-MIN_NUM_FORMS": "0",
            "unit_word_relations-MAX_NUM_FORMS": "1000",
            "unit_word_relations-0-word": str(word.pk),
            "unit_word_relations-0-example_sentence": "",
            "unit_word_relations-0-example_sentence_check_status": "NOT_CHECKED",
        },
    )

    assert response.status_code == 302, response.status_code
    assert Unit.objects.filter(title="New unit", jobs=area_job).exists()


def test_area_admin_is_restricted_to_superusers(
    db: None, request_factory: RequestFactory
) -> None:
    """Areas decide who sees what, so only superusers may manage them."""
    area_admin = AreaAdmin(Area, admin.site)
    plain_request = _get_request(request_factory, _user("plain"))
    superuser_request = _get_request(request_factory, _user("root", is_superuser=True))

    assert area_admin.has_module_permission(plain_request) is False
    assert area_admin.has_view_permission(plain_request) is False
    assert area_admin.has_add_permission(plain_request) is False
    assert area_admin.has_change_permission(plain_request) is False
    assert area_admin.has_delete_permission(plain_request) is False
    assert area_admin.has_module_permission(superuser_request) is True
    assert area_admin.has_change_permission(superuser_request) is True


def test_additional_information_url_field_is_full_width(
    db: None, request_factory: RequestFactory
) -> None:
    """The link is long, so its field must not shrink to the default size."""
    area_admin = AreaAdmin(Area, admin.site)
    superuser_request = _get_request(request_factory, _user("root", is_superuser=True))

    form_class = area_admin.get_form(superuser_request)

    widget = form_class.base_fields["additional_information_url"].widget
    assert "width: 100%" in widget.attrs.get("style", "")


def _rendered_codes(response: Any) -> list[str]:
    """The codes the rendered code inline of the given response shows."""
    return re.findall(
        r'name="codes-\d+-code"[^>]*value="([^"]*)"', response.content.decode()
    )


def test_the_code_of_a_saved_area_stays_the_same_on_every_visit(
    area: Area, client: Client
) -> None:
    """
    The code inline of an existing area shows the stored codes and nothing
    else, so a reload never looks as if a code had changed.
    """
    superuser = get_user_model().objects.create_superuser(
        username="root-stable", email="root@example.com", password="secret"
    )
    client.force_login(superuser)
    AreaCode.objects.create(area=area, code="KOLPING1")
    url = f"/en/admin/cmsv2/area/{area.pk}/change/"

    assert _rendered_codes(client.get(url)) == ["KOLPING1"]
    assert _rendered_codes(client.get(url)) == ["KOLPING1"]


@pytest.mark.django_db
def test_a_new_area_is_saved_with_the_typed_code(client: Client) -> None:
    """
    The add page of an area suggests no code, and the code that is typed into
    the empty row is the one that is stored.
    """
    superuser = get_user_model().objects.create_superuser(
        username="root-typed", email="root@example.com", password="secret"
    )
    client.force_login(superuser)

    assert _rendered_codes(client.get("/en/admin/cmsv2/area/add/")) == []

    response = client.post(
        "/en/admin/cmsv2/area/add/",
        {
            "name": "Typed",
            "admins": [],
            "codes-TOTAL_FORMS": "1",
            "codes-INITIAL_FORMS": "0",
            "codes-MIN_NUM_FORMS": "0",
            "codes-MAX_NUM_FORMS": "1000",
            "codes-0-id": "",
            "codes-0-code": "TESTKURS2026",
            "access_tokens-TOTAL_FORMS": "0",
            "access_tokens-INITIAL_FORMS": "0",
            "access_tokens-MIN_NUM_FORMS": "0",
            "access_tokens-MAX_NUM_FORMS": "0",
        },
    )

    assert response.status_code == 302
    saved_area = Area.objects.get(name="Typed")
    assert list(saved_area.codes.values_list("code", flat=True)) == ["TESTKURS2026"]


def test_the_code_count_of_the_area_list_counts_the_stored_codes(
    area: Area, client: Client
) -> None:
    """The codes column of the area list shows how many codes are stored."""
    superuser = get_user_model().objects.create_superuser(
        username="root-count", email="root@example.com", password="secret"
    )
    client.force_login(superuser)
    AreaCode.objects.create(area=area, code="KOLPING1")
    AreaCode.objects.create(area=area, code="KOLPING2")

    response = client.get("/en/admin/cmsv2/area/")

    assert b'<td class="field-number_codes">2</td>' in response.content
