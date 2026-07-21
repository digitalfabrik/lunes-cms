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


@pytest.mark.django_db
def test_word_admin_page_shows_alternative_words_section(word: Word) -> None:
    """The word admin page contains the alternative words inline and no
    Miscellaneous section anymore."""
    admin_user = User.objects.create_superuser("admin-573", "admin@example.com", "pw")
    client = Client()
    client.force_login(admin_user)
    response = client.get(f"/en/admin/cmsv2/word/{word.pk}/change/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "So heißt das auch" in content
    assert "Semmel" in content
    assert "Miscellaneous" not in content
