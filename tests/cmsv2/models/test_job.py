"""
Tests for the Job model invariant that archived jobs are never published
(issue #890).
"""

import pytest

from lunes_cms.cmsv2.models import Job


@pytest.mark.django_db()
def test_archived_job_is_unpublished_on_create() -> None:
    """Creating a job as archived must force it to be unreleased."""
    job = Job.objects.create(name="Gärtner/-in", released=True, archived=True)

    assert job.released is False


@pytest.mark.django_db()
def test_archiving_via_save_unpublishes() -> None:
    """Setting ``archived`` on an existing released job unpublishes it on save."""
    job = Job.objects.create(name="Tischler/-in", released=True)

    job.archived = True
    job.save()

    job.refresh_from_db()
    assert job.archived is True
    assert job.released is False


@pytest.mark.django_db()
def test_restoring_does_not_republish() -> None:
    """Un-archiving must leave the job unreleased until explicitly published."""
    job = Job.objects.create(name="Schlosser/-in", archived=True)

    job.archived = False
    job.save()

    job.refresh_from_db()
    assert job.archived is False
    assert job.released is False
