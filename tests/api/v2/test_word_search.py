"""
Tests for the ``search`` query parameter of the public ``/api/v2/words/``
endpoint that backs the Bildschatz website.
"""

from __future__ import annotations

import pytest
from django.test import Client

# The load_test_data fixture is injected for its side effect (loading the DB).
# pylint: disable=unused-argument

#: The public words endpoint of the second API version
WORDS_ENDPOINT = "/api/v2/words/"


@pytest.mark.django_db
def test_search_filters_words_case_insensitively(load_test_data: None) -> None:
    """A ``search`` term keeps only the words that contain it (case-insensitive)."""
    client = Client()
    response = client.get(WORDS_ENDPOINT, {"search": "schraube"})

    assert response.status_code == 200
    words = response.json()
    assert words, "expected at least one word matching 'schraube'"
    assert all("schraube" in word["word"].lower() for word in words)


@pytest.mark.parametrize("term", ["", "a", "ab", "  x "])
@pytest.mark.django_db
def test_search_shorter_than_three_characters_is_rejected(
    load_test_data: None, term: str
) -> None:
    """A ``search`` term with fewer than three characters returns HTTP 400."""
    client = Client()
    response = client.get(WORDS_ENDPOINT, {"search": term})

    assert response.status_code == 400
    assert "search" in response.json()


@pytest.mark.django_db
def test_search_with_exactly_three_characters_is_accepted(load_test_data: None) -> None:
    """A ``search`` term with exactly three characters is accepted."""
    client = Client()
    response = client.get(WORDS_ENDPOINT, {"search": "sch"})

    assert response.status_code == 200
    assert all("sch" in word["word"].lower() for word in response.json())


@pytest.mark.django_db
def test_search_is_a_subset_of_the_full_list(load_test_data: None) -> None:
    """Searching never returns words that are not part of the unfiltered list."""
    client = Client()
    all_ids = {word["id"] for word in client.get(WORDS_ENDPOINT).json()}
    search_ids = {
        word["id"] for word in client.get(WORDS_ENDPOINT, {"search": "schraube"}).json()
    }

    assert search_ids
    assert search_ids <= all_ids


@pytest.mark.django_db
def test_no_search_param_returns_the_full_unfiltered_list(load_test_data: None) -> None:
    """Without a ``search`` term the endpoint returns every public word."""
    client = Client()
    response = client.get(WORDS_ENDPOINT)

    assert response.status_code == 200
    all_words = response.json()
    matching = client.get(WORDS_ENDPOINT, {"search": "schraube"}).json()
    # The unfiltered list is a strict superset of any search result.
    assert len(all_words) > len(matching) > 0


@pytest.mark.django_db
def test_search_returns_every_public_image_of_a_word(load_test_data: None) -> None:
    """
    When searching, a word exposes all of its public images, including the ones
    defined on its released unit relations, and never fewer than the default
    listing does.
    """
    client = Client()
    default_images = {
        word["id"]: word["images"] for word in client.get(WORDS_ENDPOINT).json()
    }

    for word in client.get(WORDS_ENDPOINT, {"search": "schraube"}).json():
        assert word["images"], f"word {word['word']} should have at least one image"
        assert len(word["images"]) >= len(default_images.get(word["id"], []))
