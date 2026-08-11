"""
Tests for WordAdmin's ``?next=`` redirect override on delete (issue #531).
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Word

pytestmark = pytest.mark.django_db


def test_delete_redirects_to_next_when_given_and_safe(admin_client: Client) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    duplicated_vocabulary_url = reverse("cmsv2:duplicated_vocabulary")

    response = admin_client.post(
        f"{reverse('admin:cmsv2_word_delete', args=[word.pk])}?next={duplicated_vocabulary_url}",
        {"post": "yes"},
    )

    assert response.status_code == 302
    assert response["Location"] == duplicated_vocabulary_url
    assert not Word.objects.filter(pk=word.pk).exists()


def test_delete_with_next_still_shows_success_message(admin_client: Client) -> None:
    """The redirect override must not swallow the usual "was deleted
    successfully" message - only change where it ends up."""
    word = Word.objects.create(word="Hammer", singular_article=1)
    duplicated_vocabulary_url = reverse("cmsv2:duplicated_vocabulary")

    response = admin_client.post(
        f"{reverse('admin:cmsv2_word_delete', args=[word.pk])}?next={duplicated_vocabulary_url}",
        {"post": "yes"},
        follow=True,
    )

    assert response.redirect_chain == [(duplicated_vocabulary_url, 302)]
    messages = [str(m) for m in response.context["messages"]]
    assert any("was deleted successfully" in m for m in messages)


def test_delete_falls_back_to_changelist_without_next(admin_client: Client) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.post(
        reverse("admin:cmsv2_word_delete", args=[word.pk]), {"post": "yes"}
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("admin:cmsv2_word_changelist")


def test_delete_ignores_unsafe_next(admin_client: Client) -> None:
    """An off-site ``next`` must never be honoured - open-redirect protection."""
    word = Word.objects.create(word="Hammer", singular_article=1)

    response = admin_client.post(
        f"{reverse('admin:cmsv2_word_delete', args=[word.pk])}?next=https://evil.example/",
        {"post": "yes"},
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("admin:cmsv2_word_changelist")
