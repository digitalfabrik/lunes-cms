"""
Tests for the access gate of Bildschatz: until it is released to the public, the
website and the word search require a login to the CMS.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import Client

# The load_test_data fixture is injected for its side effect (loading the DB).
# pylint: disable=unused-argument

#: The URL of the Bildschatz website
BILDSCHATZ_URL = "/bildschatz/"

#: The words endpoint the website searches
WORDS_ENDPOINT = "/api/v2/words/"


@pytest.mark.django_db
def test_website_redirects_to_login() -> None:
    """Visitors without a login are sent to the login and back afterwards."""
    response = Client().get(BILDSCHATZ_URL, {"q": "Messer"})

    assert response.status_code == 302
    assert response["Location"].startswith(settings.LOGIN_URL)
    assert "next=/bildschatz/%3Fq%3DMesser" in response["Location"]


@pytest.mark.django_db
def test_website_is_shown_after_login(logged_in_client: Client) -> None:
    """Users logged in to the CMS see the website."""
    response = logged_in_client.get(BILDSCHATZ_URL)

    assert response.status_code == 200


@pytest.mark.django_db
def test_search_is_rejected_without_login(load_test_data: None) -> None:
    """Searching without a login is rejected with HTTP 403."""
    response = Client().get(WORDS_ENDPOINT, {"search": "schraube"})

    assert response.status_code == 403


@pytest.mark.django_db
def test_search_works_after_login(
    load_test_data: None, logged_in_client: Client
) -> None:
    """Users logged in to the CMS can search."""
    response = logged_in_client.get(WORDS_ENDPOINT, {"search": "schraube"})

    assert response.status_code == 200
    assert response.json()


@pytest.mark.django_db
def test_word_list_without_search_stays_open(
    load_test_data: None,
) -> None:
    """The gate only covers the search, the word list the app uses stays open."""
    response = Client().get(WORDS_ENDPOINT)

    assert response.status_code == 200
    assert response.json()
