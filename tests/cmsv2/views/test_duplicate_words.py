"""
Tests for the "Duplicated vocabulary" analysis views (issue #531).
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import AcceptedWordDuplicate, Job, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


def _make_unit(job: Job, title: str = "Werkzeuge") -> Unit:
    unit = Unit.objects.create(title=title)
    unit.jobs.add(job)
    return unit


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


@pytest.mark.django_db()
def test_delete_duplicate_word_get_shows_extra_unit(admin_client: Client) -> None:
    job = Job.objects.create(name="Tischler")
    unit_keeper = _make_unit(job, title="Werkzeuge")
    unit_loser = _make_unit(job, title="Baustelle")
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=unit_keeper, word=keeper)
    UnitWordRelation.objects.create(unit=unit_loser, word=loser)

    response = admin_client.get(
        reverse("cmsv2:delete_duplicate_word"), {"keeper": keeper.pk, "loser": loser.pk}
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Baustelle" in content
    assert "Vocabulary Management v2" in content


@pytest.mark.django_db()
def test_delete_duplicate_word_get_links_both_words(admin_client: Client) -> None:
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.get(
        reverse("cmsv2:delete_duplicate_word"), {"keeper": keeper.pk, "loser": loser.pk}
    )

    content = response.content.decode()
    assert reverse("admin:cmsv2_word_change", args=[keeper.pk]) in content
    assert reverse("admin:cmsv2_word_change", args=[loser.pk]) in content


@pytest.mark.django_db()
def test_delete_duplicate_word_get_with_no_relations_at_all(
    admin_client: Client,
) -> None:
    """Both duplicates are orphans (no unit relation) — must render fine, no unit questions."""
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.get(
        reverse("cmsv2:delete_duplicate_word"), {"keeper": keeper.pk, "loser": loser.pk}
    )

    assert response.status_code == 200


@pytest.mark.django_db()
def test_delete_duplicate_word_post_deletes_loser(admin_client: Client) -> None:
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.post(
        reverse("cmsv2:delete_duplicate_word"), {"keeper": keeper.pk, "loser": loser.pk}
    )

    assert response.status_code == 302
    assert not Word.objects.filter(pk=loser.pk).exists()
    assert Word.objects.filter(pk=keeper.pk).exists()


@pytest.mark.django_db()
def test_delete_duplicate_word_post_yes_carries_unit_over(admin_client: Client) -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job, title="Baustelle")
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=loser)

    admin_client.post(
        reverse("cmsv2:delete_duplicate_word"),
        {
            "keeper": keeper.pk,
            "loser": loser.pk,
            f"add_to_unit_{unit.pk}": "yes",
        },
    )

    assert keeper.units.filter(pk=unit.pk).exists()


@pytest.mark.django_db()
def test_delete_duplicate_word_post_no_drops_unit(admin_client: Client) -> None:
    job = Job.objects.create(name="Tischler")
    unit = _make_unit(job, title="Baustelle")
    keeper = Word.objects.create(word="Hammer", singular_article=1)
    loser = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=unit, word=loser)

    admin_client.post(
        reverse("cmsv2:delete_duplicate_word"),
        {
            "keeper": keeper.pk,
            "loser": loser.pk,
            f"add_to_unit_{unit.pk}": "no",
        },
    )

    assert not keeper.units.filter(pk=unit.pk).exists()


@pytest.mark.django_db()
def test_delete_duplicate_word_rejects_deleting_as_duplicate_of_itself(
    admin_client: Client,
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.get(
        reverse("cmsv2:delete_duplicate_word"), {"keeper": word.pk, "loser": word.pk}
    )

    assert response.status_code == 302
    assert Word.objects.filter(pk=word.pk).exists()
