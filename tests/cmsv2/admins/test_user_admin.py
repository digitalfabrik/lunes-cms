"""
Tests for the admin login form.
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
def staff_user(db: None) -> User:
    return get_user_model().objects.create_user(
        username="staff_member",
        email="staff@example.com",
        password=PASSWORD,
        is_staff=True,
    )


@pytest.fixture
def non_staff_user(db: None) -> User:
    return get_user_model().objects.create_user(
        username="no_staff",
        email="no-staff@example.com",
        password=PASSWORD,
        is_staff=False,
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


def test_non_staff_user_is_told_about_the_missing_permission(
    client: Client, non_staff_user: User
) -> None:
    """Valid credentials without staff status name the missing permission."""
    response = _login(client, non_staff_user.username, PASSWORD)

    assert response.status_code == 200
    assert _error_codes(response) == ["no_staff"]
    assert "not allowed to use the Lunes administration" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_wrong_password_does_not_mention_staff_status(
    client: Client, staff_user: User
) -> None:
    """A wrong password is reported as such, without mentioning staff status."""
    response = _login(client, staff_user.username, "wrong-password")

    assert response.status_code == 200
    assert _error_codes(response) == ["invalid_login"]
    assert "staff" not in response.content.decode().lower()


def test_inactive_user_is_rejected_before_the_staff_check(
    client: Client, staff_user: User
) -> None:
    """
    An inactive account is turned away by the authentication backend, so it
    never reaches the staff check and must not be told about staff status.
    """
    staff_user.is_active = False
    staff_user.save()

    response = _login(client, staff_user.username, PASSWORD)

    assert response.status_code == 200
    assert _error_codes(response) == ["invalid_login"]
    assert "_auth_user_id" not in client.session


def test_staff_user_can_log_in(client: Client, staff_user: User) -> None:
    """A staff account with correct credentials reaches the admin."""
    response = _login(client, staff_user.username, PASSWORD)

    assert response.status_code == 302
    assert "_auth_user_id" in client.session


def test_add_page_offers_staff_status(admin_client: Client) -> None:
    """The add-user page renders the staff checkbox, pre-checked."""
    response = admin_client.get(reverse("admin:auth_user_add"))

    assert response.status_code == 200
    assert response.context["adminform"].form.fields["is_staff"].initial is True
