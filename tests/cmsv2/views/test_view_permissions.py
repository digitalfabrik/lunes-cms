"""
Tests that the admin endpoints check model permissions.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.test.client import Client
from django.contrib.auth.models import User
from django.urls import reverse

from lunes_cms.cmsv2 import urls as cmsv2_urls
from lunes_cms.cmsv2.models import Job, Unit, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation

pytestmark = pytest.mark.django_db


def _all_endpoint_urls() -> list[str]:
    """Every url the cmsv2 urlconf serves, with a placeholder for each argument."""
    return [
        reverse(
            f"cmsv2:{pattern.name}",
            kwargs={name: "1" for name in pattern.pattern.regex.groupindex},
        )
        for pattern in cmsv2_urls.urlpatterns
    ]


@pytest.fixture(name="word")
def fixture_word() -> Word:
    return Word.objects.create(word="Brötchen", singular_article=3)


@pytest.fixture(name="unitword")
def fixture_unitword(word: Word) -> UnitWordRelation:
    unit = Unit.objects.create(title="Frühstück")
    return UnitWordRelation.objects.create(unit=unit, word=word)


def test_word_endpoint_denies_user_without_word_permission(
    client_with_permissions: Callable[..., Client], word: Word
) -> None:
    url = reverse("cmsv2:update_word_image_check_status", args=[word.pk])

    response = client_with_permissions("view_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 403
    assert response.json()["status"] == "error"
    word.refresh_from_db()
    assert word.image_check_status == CheckStatus.NOT_CHECKED


def test_word_endpoint_allows_user_with_word_permission(
    client_with_permissions: Callable[..., Client], word: Word
) -> None:
    url = reverse("cmsv2:update_word_image_check_status", args=[word.pk])

    response = client_with_permissions("change_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_unitword_endpoint_denies_word_only_permission(
    client_with_permissions: Callable[..., Client],
    unitword: UnitWordRelation,
) -> None:
    """Changing words does not imply changing their unit-specific data."""
    url = reverse("cmsv2:update_unitword_image_check_status", args=[unitword.pk])

    response = client_with_permissions("change_word").post(
        url, {"image_check_status": CheckStatus.CONFIRMED}
    )

    assert response.status_code == 403


def test_job_icon_endpoint_denies_user_without_job_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    job = Job.objects.create(name="Bäcker")
    url = reverse("cmsv2:update_job_icon", args=[job.pk])

    response = client_with_permissions("change_word").post(url)

    assert response.status_code == 403


def test_unit_icon_endpoint_denies_user_without_unit_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    unit = Unit.objects.create(title="Frühstück")
    url = reverse("cmsv2:update_unit_icon", args=[unit.pk])

    response = client_with_permissions("change_word").post(url)

    assert response.status_code == 403


def test_image_generation_accepts_either_content_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    """The shared image generation endpoint serves word and unit-word editors."""
    url = reverse("cmsv2:generate_image_via_openai")

    assert client_with_permissions("view_word").post(url).status_code == 403
    assert client_with_permissions("change_word").post(url).status_code != 403
    assert (
        client_with_permissions("change_unitwordrelation").post(url).status_code != 403
    )


def test_csv_import_denies_user_without_add_permission(
    client_with_permissions: Callable[..., Client],
) -> None:
    response = client_with_permissions("change_word").get(reverse("cmsv2:import_csv"))

    assert response.status_code == 403


def test_every_endpoint_requires_login(client: Client) -> None:
    """No cmsv2 endpoint is reachable without logging in."""
    reachable = [
        url for url in _all_endpoint_urls() if client.post(url).status_code != 302
    ]

    assert not reachable


def test_every_endpoint_enforces_csrf(db: None) -> None:
    """No cmsv2 endpoint accepts a post without a CSRF token."""
    superuser = User.objects.create_superuser("csrf-probe", "probe@example.com", "pw")
    strict_client = Client(enforce_csrf_checks=True)
    strict_client.force_login(superuser)

    accepted = [
        url
        for url in _all_endpoint_urls()
        if strict_client.post(url).status_code != 403
    ]

    assert not accepted
