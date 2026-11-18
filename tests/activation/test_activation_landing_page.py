"""
Tests for the ``/activation/<code>`` landing page (issue #996).

This page is what a browser reaches when a Lunes activation link/QR code is
opened without the app installed (or the OS did not route the App/Universal
Link to it) - it must be reachable without any login, must not error and
must surface the code, the store links and a deeplink retry button.

``<code>`` is an opaque identifier (not necessarily a
:class:`~lunes_cms.cms.models.group_api_key.GroupAPIKey` token), so it is
accepted as any non-empty path segment - these tests use a lower case,
non-token-shaped example on purpose to cover that.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import Area


@pytest.fixture(autouse=True)
def landing_page_area(db: None) -> Area:
    """The area whose branding the landing page shows."""
    return Area.objects.create(
        name="telc",
        is_landing_page_area=True,
        secondary_logo="area_logos/telc.svg",
    )


@pytest.mark.django_db()
def test_activation_landing_page_reachable_without_login(client: Client) -> None:
    """The page must not require authentication."""
    response = client.get(
        reverse("activation-landing-page", kwargs={"code": "dashk21"})
    )

    assert response.status_code == 200


@pytest.mark.django_db()
def test_activation_landing_page_renders_without_secondary_logo(
    client: Client, landing_page_area: Area
) -> None:
    """The secondary logo is optional, so the page must render without it."""
    landing_page_area.secondary_logo = ""
    landing_page_area.save()

    response = client.get(
        reverse("activation-landing-page", kwargs={"code": "dashk21"})
    )

    assert response.status_code == 200
    assert "colored-logo" not in response.content.decode()


@pytest.mark.django_db()
def test_activation_landing_page_contains_code_and_links(client: Client) -> None:
    """The page must surface the code (for manual entry in the app), a
    deeplink retry button and both store links."""
    code = "dashk21"
    response = client.get(reverse("activation-landing-page", kwargs={"code": code}))
    content = response.content.decode()

    assert code in content
    assert f"lunes:lunes.app/activation/{code}" in content
    assert "play.google.com/store/apps/details?id=app.lunes" in content
    assert "apps.apple.com/de/app/lunes/id1562834995" in content
    assert 'data-copy-target="activation-code"' in content


@pytest.mark.django_db()
def test_activation_landing_page_redirects_without_trailing_slash(
    client: Client,
) -> None:
    """A deeplink/QR code without a trailing slash (as printed) must still
    reach the page, via Django's default ``APPEND_SLASH`` redirect."""
    response = client.get("/activation/dashk21", follow=True)

    assert response.status_code == 200
    assert response.redirect_chain == [("/activation/dashk21/", 301)]


@pytest.mark.django_db()
def test_activation_landing_page_not_found_without_landing_page_area(
    client: Client, landing_page_area: Area
) -> None:
    """Without a marked area there is no branding to show, so there is no page."""
    landing_page_area.is_landing_page_area = False
    landing_page_area.save()

    response = client.get(
        reverse("activation-landing-page", kwargs={"code": "dashk21"})
    )

    assert response.status_code == 404


@pytest.mark.django_db()
def test_activation_landing_page_requires_a_code(client: Client) -> None:
    """An empty code must not resolve to the landing page."""
    response = client.get("/activation/")

    assert response.status_code == 404
