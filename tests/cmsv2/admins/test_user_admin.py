"""
Tests for admin access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse

PASSWORD = "supersecret123"


@pytest.fixture
def user(db: None) -> User:
    return get_user_model().objects.create_user(
        username="editor",
        email="editor@example.com",
        password=PASSWORD,
    )


def _login(client: Client, username: str, password: str) -> _MonkeyPatchedWSGIResponse:
    return client.post(
        reverse("admin:login"),
        {"username": username, "password": password},
    )


def _error_codes(response: _MonkeyPatchedWSGIResponse) -> list[str]:
    """Collect the validation codes the login form rejected the attempt with."""
    errors = response.context["form"].errors.as_data()
    return [error.code for field in errors.values() for error in field]


def test_any_active_user_can_log_in(client: Client, user: User) -> None:
    """An active account can reach the admin."""
    response = _login(client, user.username, PASSWORD)

    assert response.status_code == 302
    assert "_auth_user_id" in client.session


def test_wrong_password_is_rejected(client: Client, user: User) -> None:
    """A wrong password is rejected."""
    response = _login(client, user.username, "wrong-password")

    assert response.status_code == 200
    assert _error_codes(response) == ["invalid_login"]
    assert "_auth_user_id" not in client.session


def test_inactive_user_is_rejected(client: Client, user: User) -> None:
    """A deactivated account cannot log in."""
    user.is_active = False
    user.save()

    response = _login(client, user.username, PASSWORD)

    assert response.status_code == 200
    assert _error_codes(response) == ["invalid_login"]
    assert "_auth_user_id" not in client.session


def test_index_is_reachable_without_permissions(client: Client, user: User) -> None:
    """The dashboard renders for a logged-in account that may not change anything."""
    client.force_login(user)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200


def test_model_pages_stay_permission_gated(client: Client, user: User) -> None:
    """Logging in grants no content access on its own."""
    client.force_login(user)

    response = client.get(reverse("admin:cmsv2_word_changelist"))

    assert response.status_code == 403
