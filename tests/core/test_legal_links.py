"""
Tests for the privacy policy and imprint links.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from lunes_cms.core.utils import legal_menu_links

PRIVACY_POLICY_URL = "https://lunes.app/datenschutz"
IMPRINT_URL = "https://www.tuerantuer.org/impressum"


@pytest.mark.django_db
@override_settings(PRIVACY_POLICY_URL=PRIVACY_POLICY_URL, IMPRINT_URL=IMPRINT_URL)
def test_login_page_shows_legal_links(client: Client) -> None:
    """Both links have to be reachable without being logged in."""
    content = client.get(reverse("admin:login")).content.decode()
    assert PRIVACY_POLICY_URL in content
    assert IMPRINT_URL in content


@pytest.mark.django_db
@override_settings(PRIVACY_POLICY_URL="", IMPRINT_URL="")
def test_login_page_without_configured_urls_shows_no_legal_links(
    client: Client,
) -> None:
    """Without configured URLs, no empty links may be rendered."""
    content = client.get(reverse("admin:login")).content.decode()
    assert "legal-links" not in content


@pytest.mark.django_db
@override_settings(PRIVACY_POLICY_URL=PRIVACY_POLICY_URL, IMPRINT_URL=IMPRINT_URL)
def test_admin_footer_shows_legal_links(client: Client) -> None:
    """The admin footer carries the links on every page of the admin."""
    user = User.objects.create_superuser("legal-test", "legal@example.com", "password")
    client.force_login(user)
    content = client.get(reverse("admin:index")).content.decode()
    assert PRIVACY_POLICY_URL in content
    assert IMPRINT_URL in content


def test_legal_menu_links_skips_unconfigured_urls() -> None:
    """A link without a URL must not end up in the user menu."""
    assert legal_menu_links("", "") == []
    links = legal_menu_links(PRIVACY_POLICY_URL, "")
    assert [link["url"] for link in links] == [PRIVACY_POLICY_URL]


def test_legal_menu_links_open_in_new_window() -> None:
    """Both links leave the admin, so they must not replace the current tab."""
    links = legal_menu_links(PRIVACY_POLICY_URL, IMPRINT_URL)
    assert [link["url"] for link in links] == [PRIVACY_POLICY_URL, IMPRINT_URL]
    assert all(link["new_window"] for link in links)
