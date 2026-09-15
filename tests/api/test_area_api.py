"""
API tests ensuring the content of an area is not published to a client that
does not send the access token of that area.

These are the tests of the main app: a client that knows nothing about areas
sees exactly what it saw before areas existed. What a client with a token sees
is tested in :mod:`tests.api.test_area_token_api`.
"""

import pytest
from django.test.client import Client

from lunes_cms.cmsv2.models import Area, Job

from .area_content import (
    JOBS_ENDPOINT,
    released_unit_with_word,
    UNITS_ENDPOINT,
    WORDS_ENDPOINT,
)


@pytest.mark.django_db()
def test_job_of_an_area_not_listed_in_api():
    """A released job that belongs to an area must not appear in the job list."""
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)
    main_job = Job.objects.create(name="Main job", released=True)

    response = Client().get(JOBS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {job["id"] for job in response.json()}
    assert main_job.pk in returned_ids
    assert area_job.pk not in returned_ids


@pytest.mark.django_db()
def test_units_and_words_of_an_area_job_denied():
    """The units and words of a job of an area are not accessible."""
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)

    units_response = Client().get(f"{JOBS_ENDPOINT}{area_job.pk}/units/")
    words_response = Client().get(f"{JOBS_ENDPOINT}{area_job.pk}/words/")

    assert units_response.status_code in (403, 404)
    assert words_response.status_code in (403, 404)


@pytest.mark.django_db()
def test_words_of_an_area_unit_denied():
    """The words of a unit that belongs to an area are not accessible."""
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)
    unit, _word = released_unit_with_word(area_job, "Area unit", "Bereichswort")

    response = Client().get(f"{UNITS_ENDPOINT}{unit.pk}/words/")

    assert response.status_code in (403, 404)


@pytest.mark.django_db()
def test_unit_shared_with_an_area_job_is_not_published():
    """
    A unit that belongs to a main app job and to a job of an area must not be
    published: the filter has to reject the unit because one of its jobs has an
    area, not accept it because another one has none.
    """
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)
    main_job = Job.objects.create(name="Main job", released=True)
    unit, word = released_unit_with_word(main_job, "Shared unit", "Bereichswort")
    unit.jobs.add(area_job)

    unit_words = Client().get(f"{UNITS_ENDPOINT}{unit.pk}/words/")
    job_units = Client().get(f"{JOBS_ENDPOINT}{main_job.pk}/units/")
    job_words = Client().get(f"{JOBS_ENDPOINT}{main_job.pk}/words/")
    word_list = Client().get(WORDS_ENDPOINT)

    assert unit_words.status_code in (403, 404)
    assert unit.pk not in {returned["id"] for returned in job_units.json()}
    assert word.pk not in {returned["id"] for returned in job_words.json()}
    assert word.pk not in {returned["id"] for returned in word_list.json()}


@pytest.mark.django_db()
def test_word_list_excludes_words_of_an_area():
    """The word list only contains words of the main app."""
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)
    main_job = Job.objects.create(name="Main job", released=True)
    _area_unit, area_word = released_unit_with_word(
        area_job, "Area unit", "Bereichswort"
    )
    _main_unit, main_word = released_unit_with_word(main_job, "Main unit", "Hauptwort")

    response = Client().get(WORDS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {word["id"] for word in response.json()}
    assert main_word.pk in returned_ids
    assert area_word.pk not in returned_ids
