"""
Tests for alternative words (issue #573): serialization in the v2 API
and the "So heißt das auch" inline on the word admin page.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.test.client import Client

from lunes_cms.api.v2.serializers import UnitWordRelationSerializer, WordSerializer
from lunes_cms.cmsv2.models import AlternativeWord, Unit, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation


@pytest.fixture(name="word")
def fixture_word(db: None) -> Word:
    """A word with one alternative word."""
    word = Word.objects.create(word="Brötchen", singular_article=3)
    AlternativeWord.objects.create(word=word, alt_word="Semmel", singular_article=2)
    return word


@pytest.mark.django_db
def test_word_serializer_contains_alternative_words(word: Word) -> None:
    """The word serializer exposes the alternative words of a word."""
    data = WordSerializer(word).data
    assert data["alternative_words"] == [{"alt_word": "Semmel", "article": "die"}]


@pytest.mark.django_db
def test_unit_word_relation_serializer_contains_alternative_words(word: Word) -> None:
    """The unit word relation serializer exposes the alternative words of its word."""
    unit = Unit.objects.create(title="Backwaren")
    relation = UnitWordRelation.objects.create(unit=unit, word=word)
    data = UnitWordRelationSerializer(relation).data
    assert data["alternative_words"] == [{"alt_word": "Semmel", "article": "die"}]


@pytest.mark.django_db
def test_alternative_word_without_article_serializes_empty_article(word: Word) -> None:
    """An alternative word without a singular article serializes to an empty string."""
    AlternativeWord.objects.create(word=word, alt_word="Weck")
    data = WordSerializer(word).data
    assert {"alt_word": "Weck", "article": ""} in data["alternative_words"]


@pytest.fixture(name="admin_client")
def fixture_admin_client(db: None) -> Client:
    """A client logged in as a superuser."""
    admin_user = User.objects.create_superuser("admin-573", "admin@example.com", "pw")
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.mark.django_db
def test_word_admin_page_shows_alternative_words_section(
    word: Word, admin_client: Client
) -> None:
    """The word admin page contains the alternative words inline with a delete
    button per saved row and no Miscellaneous section anymore."""
    response = admin_client.get(f"/en/admin/cmsv2/word/{word.pk}/change/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "So heißt das auch" in content
    assert "Semmel" in content
    assert "Miscellaneous" not in content
    assert "save-alternative-word-btn" in content
    assert "delete-alternative-word-btn" in content
    # the extra row gets an instant add button
    assert "add-alternative-word-btn" in content
    # the default formset delete checkbox is replaced by the instant delete button
    assert "alternative_words-0-DELETE" not in content


@pytest.mark.django_db
def test_delete_alternative_word(word: Word, admin_client: Client) -> None:
    """The delete view removes the alternative word."""
    alternative_word = word.alternative_words.get()
    response = admin_client.post(
        f"/en/admin/cmsv2/alternativewords/{alternative_word.pk}/delete/"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert not word.alternative_words.exists()


@pytest.mark.django_db
def test_delete_alternative_word_not_found(admin_client: Client) -> None:
    """The delete view returns a 404 response for an unknown id."""
    response = admin_client.post("/en/admin/cmsv2/alternativewords/12345/delete/")
    assert response.status_code == 404
    assert response.json()["status"] == "error"


@pytest.mark.django_db
def test_add_alternative_word(word: Word, admin_client: Client) -> None:
    """The save view creates a new alternative word for a word."""
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"word_id": word.pk, "alt_word": "Weck", "singular_article": "1", "plural": ""},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    alternative_word = word.alternative_words.get(alt_word="Weck")
    assert alternative_word.singular_article == 1
    assert alternative_word.grammatical_gender is None


@pytest.mark.django_db
def test_save_alternative_word(word: Word, admin_client: Client) -> None:
    """The save view updates an existing alternative word."""
    alternative_word = word.alternative_words.get()
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {
            "alternative_word_id": alternative_word.pk,
            "alt_word": "Schrippe",
            "singular_article": "2",
            "plural": "Schrippen",
            "plural_article": "1",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    alternative_word.refresh_from_db()
    assert alternative_word.alt_word == "Schrippe"
    assert alternative_word.plural == "Schrippen"
    assert alternative_word.plural_article == 1


@pytest.mark.django_db
def test_save_alternative_word_requires_alt_word(
    word: Word, admin_client: Client
) -> None:
    """The save view rejects an empty alternative word."""
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"word_id": word.pk, "alt_word": "   "},
    )
    assert response.status_code == 400
    assert word.alternative_words.count() == 1


@pytest.mark.django_db
def test_save_alternative_word_invalid_article(
    word: Word, admin_client: Client
) -> None:
    """The save view rejects invalid choice values."""
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"word_id": word.pk, "alt_word": "Weck", "singular_article": "99"},
    )
    assert response.status_code == 400
    assert word.alternative_words.count() == 1


@pytest.mark.django_db
def test_save_alternative_word_unknown_word(admin_client: Client) -> None:
    """The save view returns a 404 response for an unknown word id."""
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"word_id": "12345", "alt_word": "Weck"},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_save_alternative_word_missing_word_id(admin_client: Client) -> None:
    """The save view rejects a creation request without a word id."""
    response = admin_client.post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"alt_word": "Weck"},
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_save_alternative_word_requires_staff(word: Word) -> None:
    """The save view redirects anonymous users to the login page."""
    response = Client().post(
        "/en/admin/cmsv2/alternativewords/save/",
        {"word_id": word.pk, "alt_word": "Weck"},
    )
    assert response.status_code == 302
    assert word.alternative_words.count() == 1


@pytest.mark.django_db
def test_delete_alternative_word_requires_staff(word: Word) -> None:
    """The delete view redirects anonymous users to the login page."""
    alternative_word = word.alternative_words.get()
    response = Client().post(
        f"/en/admin/cmsv2/alternativewords/{alternative_word.pk}/delete/"
    )
    assert response.status_code == 302
    assert word.alternative_words.exists()
