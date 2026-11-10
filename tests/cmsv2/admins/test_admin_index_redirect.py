"""
Tests that users who may only review are sent from the admin dashboard to
their review view, while everyone else keeps the dashboard.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client
from django.urls import reverse

from tests.cmsv2.helpers import PermissionClient

pytestmark = pytest.mark.django_db


def _user_in_group_with(*codenames: str) -> User:
    """
    Create a user whose only group grants exactly the given cmsv2 permissions.
    """
    group = Group.objects.create(name=f"group-with-{'-'.join(codenames)}")
    group.permissions.set(
        Permission.objects.filter(
            content_type__app_label="cmsv2", codename__in=codenames
        )
    )
    user = User.objects.create_user(f"user-with-{'-'.join(codenames)}")
    user.groups.add(group)
    return user


def test_only_reviewer_is_redirected_to_review_view() -> None:
    client = PermissionClient(_user_in_group_with("can_review"))

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302
    assert response.url == reverse("expert_access:index")


def test_reviewer_with_further_permissions_sees_dashboard() -> None:
    client = PermissionClient(_user_in_group_with("can_review", "view_word"))

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200


def test_superuser_sees_dashboard() -> None:
    superuser = User.objects.create_superuser("admin")
    superuser.user_permissions.add(Permission.objects.get(codename="can_review"))
    client = PermissionClient(superuser)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200


def test_login_of_only_reviewer_ends_in_review_view() -> None:
    user = _user_in_group_with("can_review")
    user.set_password("password")
    user.save()
    client = Client()

    # The admin login form sends the dashboard as ``next`` when opened directly
    response = client.post(
        reverse("admin:login"),
        {
            "username": user.username,
            "password": "password",
            "next": reverse("admin:index"),
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("admin:index")

    response = client.get(response.url)
    assert response.status_code == 302
    assert response.url == reverse("expert_access:index")
