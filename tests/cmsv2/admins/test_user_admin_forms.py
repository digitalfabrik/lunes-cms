"""
Tests that the admin user forms require an email address.
"""

import pytest
from django.contrib.auth.models import User

from lunes_cms.cmsv2.admins.user_admin import (
    LunesUserChangeForm,
    LunesUserCreationForm,
)

pytestmark = pytest.mark.django_db


def test_creating_user_without_email_is_rejected() -> None:
    """The add-user form is invalid when no email is provided."""
    form = LunesUserCreationForm(
        data={
            "username": "new.user",
            "password1": "sup3rSecret!pw",
            "password2": "sup3rSecret!pw",
        }
    )
    assert not form.is_valid()
    assert "email" in form.errors


def test_creating_user_with_email_is_accepted() -> None:
    """The add-user form is valid when an email is provided."""
    form = LunesUserCreationForm(
        data={
            "username": "new.user",
            "email": "new.user@lunes.app",
            "password1": "sup3rSecret!pw",
            "password2": "sup3rSecret!pw",
        }
    )
    assert form.is_valid(), form.errors


def test_change_form_requires_email() -> None:
    """The change form marks email as required, so it cannot be cleared on edit."""
    user = User.objects.create_user(
        username="existing.user", email="existing.user@lunes.app"
    )
    form = LunesUserChangeForm(instance=user)
    assert form.fields["email"].required
