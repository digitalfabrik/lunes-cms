"""
Tests for the "Analyse" sidebar entry that links to the duplicated
vocabulary analysis page (issue #531).
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Word


@pytest.mark.django_db()
def test_admin_index_shows_no_count_without_duplicates(admin_client: Client) -> None:
    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Duplicated vocabulary (" not in content


@pytest.mark.django_db()
def test_admin_index_shows_duplicate_count_in_sidebar(admin_client: Client) -> None:
    # A distinctive, nonsense word text: the shared session-scoped fixture
    # data (tests/conftest.py's `load_test_data`) persists real vocabulary
    # across the whole test session without a per-test rollback, so a common
    # German word here would risk colliding with it.
    Word.objects.create(word="Flimmerquastenzange", singular_article=1)
    Word.objects.create(word="Flimmerquastenzange", singular_article=1)

    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Duplicated vocabulary (1)" in content


@pytest.mark.django_db()
def test_sidebar_entry_redirects_to_analysis_page(admin_client: Client) -> None:
    response = admin_client.get(
        reverse("admin:analysis_duplicatedvocabulary_changelist")
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("cmsv2:duplicated_vocabulary")


@pytest.mark.django_db()
def test_admin_index_shows_analysis_section(admin_client: Client) -> None:
    # LANGUAGE_CODE defaults to "en" and the test client doesn't request a
    # different locale, so this renders the English source strings; German
    # translations aren't covered here (like the rest of the test suite),
    # just by the separate check-translations CI job.
    response = admin_client.get(reverse("admin:index"))

    content = response.content.decode()
    assert "Analysis" in content
    assert "Duplicated vocabulary" in content
