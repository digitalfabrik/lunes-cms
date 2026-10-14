"""
Tests for the CMS version markers on permission labels.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.admins.permission_labels import permission_label


@pytest.fixture(name="superuser_client")
def fixture_superuser_client() -> Client:
    """A client logged in as a superuser."""
    superuser = get_user_model().objects.create_superuser(
        username="root", email="root@example.com", password="supersecret123"
    )
    client = Client()
    client.force_login(superuser)
    return client


@pytest.mark.parametrize(
    "app_label, codename, marker",
    [
        ("cms", "add_discipline", "(v1) "),
        ("cmsv2", "add_word", "(v2) "),
        ("auth", "add_group", ""),
    ],
)
@pytest.mark.django_db
def test_permission_label_marks_cms_version(
    app_label: str, codename: str, marker: str
) -> None:
    """Only permissions of the v1 and v2 apps get a version marker."""
    permission = Permission.objects.select_related("content_type").get(
        content_type__app_label=app_label, codename=codename
    )
    assert permission_label(permission) == f"{marker}{permission}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name, args",
    [("admin:auth_group_add", ()), ("admin:auth_user_change", (1,))],
)
def test_permission_select_shows_cms_version(
    superuser_client: Client, url_name: str, args: tuple[int, ...]
) -> None:
    """The group and user pages list the version-marked permissions."""
    response = superuser_client.get(reverse(url_name, args=args))
    assert response.status_code == 200
    content = response.content.decode()
    assert "(v2) Word | Can add Word" in content
    assert "(v1) discipline | Can add discipline" in content
