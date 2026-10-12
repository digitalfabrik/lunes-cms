"""
API tests for the ``expert_reviewed`` quality seal of jobs (issue #762).
"""

import pytest
from django.test.client import Client

from lunes_cms.cmsv2.models import Job

from .area_content import JOBS_ENDPOINT


@pytest.mark.django_db()
def test_expert_reviewed_is_exposed_in_job_list():
    reviewed = Job.objects.create(
        name="Reviewed job", released=True, expert_reviewed=True
    )
    internal = Job.objects.create(name="Internal job", released=True)

    response = Client().get(JOBS_ENDPOINT)

    assert response.status_code == 200
    seals = {job["id"]: job["expert_reviewed"] for job in response.json()}
    assert seals[reviewed.pk] is True
    assert seals[internal.pk] is False
