"""
Tests that the admin user forms require an email address and let a
superuser assign the areas a user administers.
"""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, User
from django.test import Client, RequestFactory

from lunes_cms.cmsv2.admins.user_admin import (
    LunesUserAdmin,
    LunesUserChangeForm,
    LunesUserCreationForm,
)
from lunes_cms.cmsv2.models import Area

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


def test_change_form_shows_the_users_current_areas() -> None:
    """The field is preselected with the areas the user already administers."""
    user = User.objects.create_user(
        username="existing.user", email="existing.user@lunes.app"
    )
    area = Area.objects.create(name="Kolping")
    area.admins.add(user)

    form = LunesUserChangeForm(instance=user)

    assert list(form.fields["administered_areas"].initial) == [area]


def test_saving_the_change_form_assigns_the_selected_areas() -> None:
    """Saving the form updates which areas the user administers."""
    user = User.objects.create_user(
        username="existing.user", email="existing.user@lunes.app"
    )
    old_area = Area.objects.create(name="Old")
    old_area.admins.add(user)
    new_area = Area.objects.create(name="New")

    form = LunesUserChangeForm(instance=user)
    data = {**form.initial, "administered_areas": [new_area.pk]}
    bound_form = LunesUserChangeForm(data=data, instance=user)

    assert bound_form.is_valid(), bound_form.errors
    bound_form.save()

    assert list(user.administered_areas.all()) == [new_area]


def test_administered_areas_is_disabled_for_non_superusers() -> None:
    """Only a superuser may assign areas, the same rule ``AreaAdmin`` enforces."""
    user_admin = LunesUserAdmin(User, admin.site)
    editor = User.objects.create_user(username="editor", email="editor@example.com")
    plain_user = User.objects.create_user(username="plain", email="plain@example.com")
    superuser = User.objects.create_superuser(
        username="root", email="root@example.com", password="secret"
    )
    request = RequestFactory().get("/")

    request.user = plain_user
    plain_form_class = user_admin.get_form(request, editor)
    assert plain_form_class(instance=editor).fields["administered_areas"].disabled

    request.user = superuser
    superuser_form_class = user_admin.get_form(request, editor)
    assert (
        not superuser_form_class(instance=editor).fields["administered_areas"].disabled
    )

    # The shared field on the base form class must stay untouched, or a
    # later superuser request would inherit the disabled state.
    assert not LunesUserChangeForm.declared_fields["administered_areas"].disabled


def test_area_field_renders_editable_for_a_superuser(client: Client) -> None:
    """A superuser sees the areas field as an editable, enabled widget."""
    superuser = get_user_model().objects.create_superuser(
        username="root", email="root@example.com", password="secret"
    )
    area = Area.objects.create(name="Kolping")
    area.admins.add(superuser)
    client.force_login(superuser)

    response = client.get(f"/en/admin/auth/user/{superuser.pk}/change/")

    assert response.status_code == 200
    assert b'name="administered_areas"' in response.content
    assert b'id="id_administered_areas"' in response.content
    assert b"Kolping" in response.content


def test_area_field_renders_disabled_for_a_non_superuser(client: Client) -> None:
    """
    A non-superuser who may still edit users (e.g. via a custom permission)
    sees the assigned areas, but as a disabled widget they cannot change.
    """
    editor = get_user_model().objects.create_user(
        username="editor", email="editor@example.com", password="secret", is_staff=True
    )
    editor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="auth", codename__in=["view_user", "change_user"]
        )
    )
    area = Area.objects.create(name="Kolping")
    area.admins.add(editor)
    client.force_login(editor)

    response = client.get(f"/en/admin/auth/user/{editor.pk}/change/")

    assert response.status_code == 200
    assert b"Kolping" in response.content
    assert b'name="administered_areas"' in response.content
    assert b"disabled" in response.content


def test_a_non_superuser_cannot_change_areas_via_a_crafted_request(
    client: Client,
) -> None:
    """
    Disabling the field is a security boundary, not just a display hint: a
    submitted value for it must be ignored, not just hidden from the widget.
    """
    editor = get_user_model().objects.create_user(
        username="editor", email="editor@example.com", password="secret", is_staff=True
    )
    editor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="auth",
            codename__in=["view_user", "change_user"],
        )
    )
    own_area = Area.objects.create(name="Own")
    own_area.admins.add(editor)
    other_area = Area.objects.create(name="Other")
    client.force_login(editor)

    client.post(
        f"/en/admin/auth/user/{editor.pk}/change/",
        {
            "username": editor.username,
            "email": editor.email,
            "administered_areas": [other_area.pk],
        },
    )

    assert list(editor.administered_areas.all()) == [own_area]
