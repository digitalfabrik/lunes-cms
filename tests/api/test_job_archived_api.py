"""
API tests ensuring archived jobs are not published via the v2 API (issue #890).
"""

import pytest
from django.test.client import Client

from lunes_cms.cmsv2.models import Job

JOBS_ENDPOINT = "/api/v2/jobs/"


@pytest.mark.django_db()
def test_archived_job_not_listed_in_api():
    """A released but archived job must not appear in the public job list."""
    active = Job.objects.create(name="Active job", released=True, archived=False)
    archived = Job.objects.create(name="Archived job", released=True, archived=True)

    response = Client().get(JOBS_ENDPOINT)

    assert response.status_code == 200
    returned_ids = {job["id"] for job in response.json()}
    assert active.pk in returned_ids
    assert archived.pk not in returned_ids


@pytest.mark.django_db()
def test_archived_job_units_endpoint_denied():
    """Units of an archived job must not be served via the API."""
    archived = Job.objects.create(name="Archived job", released=True, archived=True)

    response = Client().get(f"{JOBS_ENDPOINT}{archived.pk}/units/")

    # An archived job is unpublished, so its units are not accessible.
    assert response.status_code in (403, 404)


@pytest.mark.django_db()
def test_archived_job_words_endpoint_denied():
    """Words of an archived job must not be served via the API."""
    archived = Job.objects.create(name="Archived job", released=True, archived=True)

    response = Client().get(f"{JOBS_ENDPOINT}{archived.pk}/words/")

    assert response.status_code in (403, 404)
