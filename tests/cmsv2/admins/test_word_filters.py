"""
Tests for the list filters of the word admin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client

from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation

if TYPE_CHECKING:
    from django.contrib.admin.views.main import ChangeList

    # Client.get() returns this test-only response subclass (adds .context
    # and .wsgi_request), which only exists in django-stubs.
    from django.test.client import _MonkeyPatchedWSGIResponse

URL = "/en/admin/cmsv2/word/"


@pytest.fixture
def superuser_client(db: None, client: Client) -> Client:
    superuser = get_user_model().objects.create_superuser(
        username="root-filters", email="root@example.com", password="secret"
    )
    client.force_login(superuser)
    return client


@pytest.fixture
def catalog(db: None) -> dict[str, Job | Unit | Word]:
    """Two jobs with one unit and one word each."""
    nurse = Job.objects.create(name="Nurse")
    baker = Job.objects.create(name="Baker")
    care = Unit.objects.create(title="Care")
    care.jobs.add(nurse)
    bread = Unit.objects.create(title="Bread")
    bread.jobs.add(baker)
    bandage = Word.objects.create(word="Verband", singular_article=1)
    dough = Word.objects.create(word="Teig", singular_article=1)
    UnitWordRelation.objects.create(unit=care, word=bandage)
    UnitWordRelation.objects.create(unit=bread, word=dough)
    return {
        "nurse": nurse,
        "baker": baker,
        "care": care,
        "bread": bread,
        "bandage": bandage,
        "dough": dough,
    }


def _filter_choices(
    response: _MonkeyPatchedWSGIResponse, parameter_name: str
) -> list[str]:
    changelist: ChangeList = response.context["cl"]
    for list_filter in changelist.get_filters(response.wsgi_request)[0]:
        if (
            isinstance(list_filter, admin.SimpleListFilter)
            and list_filter.parameter_name == parameter_name
        ):
            return [str(title) for _key, title in list_filter.lookup_choices]
    raise AssertionError(f"No filter with parameter {parameter_name}")


def _words(changelist: ChangeList) -> set[str]:
    return {word.word for word in changelist.result_list}


def test_unit_filter_offers_all_units_without_a_job(
    superuser_client: Client, catalog: dict[str, Job | Unit | Word]
) -> None:
    response = superuser_client.get(URL)
    assert set(_filter_choices(response, "unit")) == {"Care", "Bread"}
    assert set(_filter_choices(response, "job")) == {"Nurse", "Baker"}
    assert _words(response.context["cl"]) == {"Verband", "Teig"}


def test_unit_filter_offers_only_the_units_of_the_selected_job(
    superuser_client: Client, catalog: dict[str, Job | Unit | Word]
) -> None:
    response = superuser_client.get(URL, {"job": catalog["nurse"].pk})
    assert _filter_choices(response, "unit") == ["Care"]
    assert _words(response.context["cl"]) == {"Verband"}


def test_unit_filter_filters_the_words_of_the_selected_unit(
    superuser_client: Client, catalog: dict[str, Job | Unit | Word]
) -> None:
    changelist = superuser_client.get(
        URL, {"job": catalog["nurse"].pk, "unit": catalog["care"].pk}
    ).context["cl"]
    assert _words(changelist) == {"Verband"}


def test_unit_filter_ignores_a_unit_outside_of_the_selected_job(
    superuser_client: Client, catalog: dict[str, Job | Unit | Word]
) -> None:
    """
    After switching the job, the previously selected unit stays in the query
    string, but must neither filter the words nor appear to be selected.
    """
    response = superuser_client.get(
        URL, {"job": catalog["baker"].pk, "unit": catalog["care"].pk}
    )
    assert response.status_code == 200
    changelist = response.context["cl"]
    assert _words(changelist) == {"Teig"}
