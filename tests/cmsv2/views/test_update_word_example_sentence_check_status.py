"""
Tests for the ``update_word_example_sentence_check_status`` endpoint (#823).

Covers success/error responses and, since the view used to be wrongly
``@csrf_exempt`` on top of ``@staff_member_required`` (a security bug fixed on
this branch), that it now enforces both authentication and CSRF protection
like its sibling check-status endpoints.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import CheckStatus


@pytest.fixture(name="word")
def fixture_word(db: None) -> Word:
    return Word.objects.create(
        word="Hammer", singular_article=1, example_sentence="Der Hammer ist schwer."
    )


def _url(word: Word) -> str:
    return reverse("cmsv2:update_word_example_sentence_check_status", args=[word.pk])


@pytest.mark.django_db
def test_updates_check_status_successfully(admin_client: Client, word: Word) -> None:
    response = admin_client.post(
        _url(word), {"example_sentence_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.CONFIRMED


@pytest.mark.django_db
def test_returns_404_for_unknown_word(admin_client: Client) -> None:
    response = admin_client.post(
        reverse("cmsv2:update_word_example_sentence_check_status", args=[123456]),
        {"example_sentence_check_status": CheckStatus.CONFIRMED},
    )

    assert response.status_code == 404
    assert response.json()["status"] == "error"


@pytest.mark.django_db
def test_requires_check_status_param(admin_client: Client, word: Word) -> None:
    response = admin_client.post(_url(word))

    assert response.status_code == 400
    assert response.json()["status"] == "error"
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db
def test_rejects_get_request(admin_client: Client, word: Word) -> None:
    response = admin_client.get(_url(word))

    assert response.status_code == 405


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login(word: Word) -> None:
    response = Client().post(
        _url(word), {"example_sentence_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 302
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db
def test_non_staff_user_is_redirected_to_login(word: Word) -> None:
    non_staff = get_user_model().objects.create_user(
        username="non-staff-823", is_staff=False
    )
    client = Client()
    client.force_login(non_staff)

    response = client.post(
        _url(word), {"example_sentence_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 302
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db
def test_rejects_post_without_csrf_token(word: Word) -> None:
    """
    Regression test for #823: the view was previously ``@csrf_exempt`` next to
    ``@staff_member_required``, which is exactly backwards, since it dropped
    the CSRF protection that authenticated, cookie-based requests rely on.
    """
    admin_user = get_user_model().objects.create_superuser(
        "admin-823", "admin-823@example.com", "password"
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin_user)

    response = client.post(
        _url(word), {"example_sentence_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 403
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.NOT_CHECKED


@pytest.mark.django_db
def test_accepts_post_with_valid_csrf_token(word: Word) -> None:
    admin_user = get_user_model().objects.create_superuser(
        "admin-823-valid", "admin-823-valid@example.com", "password"
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(admin_user)
    # A GET against any page protected by CsrfViewMiddleware sets the cookie.
    client.get(reverse("admin:index"))
    csrf_token = client.cookies["csrftoken"].value

    response = client.post(
        _url(word),
        {"example_sentence_check_status": CheckStatus.CONFIRMED},
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    word.refresh_from_db()
    assert word.example_sentence_check_status == CheckStatus.CONFIRMED
