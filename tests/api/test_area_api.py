"""
API tests ensuring the content of an area is not published via the v2 API.

How a part organization receives its own area is not specified yet, so until
then no client may see area content.
"""

import pytest
from django.test.client import Client

from lunes_cms.cmsv2.models import Area, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation

JOBS_ENDPOINT = "/api/v2/jobs/"
UNITS_ENDPOINT = "/api/v2/units/"
WORDS_ENDPOINT = "/api/v2/words/"


def _released_unit_with_word(job, title, word_text):
    """Create a released unit of the job with one fully confirmed word."""
    unit = Unit.objects.create(title=title, released=True)
    unit.jobs.add(job)
    word = Word.objects.create(word=word_text, singular_article=1)
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    # ``save()`` resets the check status of an asset that is not there, so the
    # confirmations have to be written past it.
    Word.objects.filter(pk=word.pk).update(
        audio_check_status="CONFIRMED", image_check_status="CONFIRMED"
    )
    UnitWordRelation.objects.filter(pk=relation.pk).update(
        image_check_status="CONFIRMED"
    )
    word.refresh_from_db()
    return unit, word


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
    unit, _word = _released_unit_with_word(area_job, "Area unit", "Bereichswort")

    response = Client().get(f"{UNITS_ENDPOINT}{unit.pk}/words/")

    assert response.status_code in (403, 404)


@pytest.mark.django_db()
def test_word_list_excludes_words_of_an_area():
    """The word list only contains words of the main app."""
    area = Area.objects.create(name="Kolping")
    area_job = Job.objects.create(name="Area job", released=True, area=area)
    main_job = Job.objects.create(name="Main job", released=True)
    _area_unit, area_word = _released_unit_with_word(
        area_job, "Area unit", "Bereichswort"
    )
    _main_unit, main_word = _released_unit_with_word(
        main_job, "Main unit", "Hauptwort"
    )

    response = Client().get(WORDS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {word["id"] for word in response.json()}
    assert main_word.pk in returned_ids
    assert area_word.pk not in returned_ids
