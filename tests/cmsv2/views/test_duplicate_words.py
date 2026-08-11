"""
Tests for the "Open duplicates" analysis views (issue #531).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _make_unit(job: Job, title: str = "Werkzeuge") -> Unit:
    unit = Unit.objects.create(title=title)
    unit.jobs.add(job)
    return unit


def _staff_client() -> Client:
    """A logged-in staff user who is *not* a superuser."""
    user = get_user_model().objects.create_user(
        username="staff-not-admin", password="password", is_staff=True
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db()
def test_duplicated_vocabulary_denies_staff_who_is_not_superuser() -> None:
    """Only superusers may see/manage duplicate vocabulary — a plain staff
    user must be redirected (e.g. to the admin login), not let in."""
    response = _staff_client().get(reverse("cmsv2:duplicated_vocabulary"))

    assert response.status_code == 302


@pytest.mark.django_db()
def test_check_duplicate_returns_matches(admin_client: Client) -> None:
    # A distinctive, nonsense word text: the shared session-scoped fixture
    # data (tests/conftest.py's `load_test_data`) persists real vocabulary
    # like "Hammer" across the whole test session without a per-test
    # rollback, so a common German word here would risk colliding with it.
    existing = Word.objects.create(word="Flimmerquastenzange", singular_article=1)

    response = admin_client.get(
        reverse("cmsv2:word_check_duplicate"), {"word": "Flimmerquastenzange"}
    )

    assert response.status_code == 200
    matches = response.json()["matches"]
    assert [m["pk"] for m in matches] == [existing.pk]


@pytest.mark.django_db()
def test_check_duplicate_excludes_given_pk(admin_client: Client) -> None:
    existing = Word.objects.create(word="Flimmerquastenzange", singular_article=1)

    response = admin_client.get(
        reverse("cmsv2:word_check_duplicate"),
        {"word": "Flimmerquastenzange", "exclude_pk": str(existing.pk)},
    )

    assert response.json()["matches"] == []


@pytest.mark.django_db()
def test_check_duplicate_no_match_returns_empty(admin_client: Client) -> None:
    response = admin_client.get(
        reverse("cmsv2:word_check_duplicate"), {"word": "Nichtvorhanden"}
    )

    assert response.json()["matches"] == []


@pytest.mark.django_db()
def test_duplicated_vocabulary_lists_job_and_word(admin_client: Client) -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    a = Word.objects.create(word="Hammer", singular_article=1)
    b = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=a)
    UnitWordRelation.objects.create(unit=unit, word=b)

    response = admin_client.get(reverse("cmsv2:duplicated_vocabulary"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Tischler" in content
    assert "Hammer" in content


@pytest.mark.django_db()
def test_duplicated_vocabulary_offers_delete_for_the_suggested_word_too(
    admin_client: Client,
) -> None:
    """Even the "Suggested to keep" entry must be deletable - e.g. if one of
    the other duplicates should be kept instead."""
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    # A distinctive, nonsense word text - see test_check_duplicate_returns_matches.
    a = Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    b = Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=a)
    UnitWordRelation.objects.create(unit=unit, word=b)

    response = admin_client.get(reverse("cmsv2:duplicated_vocabulary"))

    content = response.content.decode()
    # Every word in the group gets Django's regular delete-confirmation page,
    # regardless of which one is suggested to keep.
    assert reverse("admin:cmsv2_word_delete", args=[a.pk]) in content
    assert reverse("admin:cmsv2_word_delete", args=[b.pk]) in content


@pytest.mark.django_db()
def test_duplicated_vocabulary_keeps_full_sidebar(admin_client: Client) -> None:
    """The page must include the admin site's normal context (available_apps
    etc.), or Jazzmin's sidebar collapses to just "Dashboard"."""
    response = admin_client.get(reverse("cmsv2:duplicated_vocabulary"))

    content = response.content.decode()
    assert "Vocabulary Management v2" in content
    assert "Jobs" in content


@pytest.mark.django_db()
def test_accept_word_duplicate_hides_group_from_list(admin_client: Client) -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job)
    a = Word.objects.create(word="Hammer", singular_article=1)
    b = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=a)
    UnitWordRelation.objects.create(unit=unit, word=b)

    response = admin_client.post(
        reverse("cmsv2:accept_word_duplicate"), {"word": [a.pk, b.pk]}
    )

    assert response.status_code == 302
    assert AcceptedWordDuplicate.objects.count() == 1
    assert set(
        AcceptedWordDuplicate.objects.get().words.values_list("pk", flat=True)
    ) == {
        a.pk,
        b.pk,
    }
    content = admin_client.get(reverse("cmsv2:duplicated_vocabulary")).content.decode()
    assert "No unresolved duplicate vocabulary found." in content
