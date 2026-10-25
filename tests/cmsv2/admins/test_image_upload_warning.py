"""
Tests for the warning not to upload images of people (#1085).

Every control in the admin that uploads a vocabulary image has to show a
warning sign before a file is chosen, which explains the warning on hover.

The pages are only requested in English: not every CI job compiles the German
translations, and a German request would leave German active for later tests.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import translation

from lunes_cms.cmsv2.models import Unit, UnitWordRelation, Word

#: The start of the rendered warning sign, unescaped and with its tooltip
WARNING_SIGN = (
    '<span class="image-upload-warning" '
    'title="Please do not upload photos in which a real person can be recognized'
)


@pytest.fixture
def admin_client(db: None) -> Client:
    client = Client()
    client.force_login(
        get_user_model().objects.create_superuser(username="admin", password="pw")
    )
    return client


@pytest.fixture
def unit_word(db: None) -> UnitWordRelation:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Werkzeug")
    return UnitWordRelation.objects.create(unit=unit, word=word)


def get_page(client: Client, url_name: str, *args: int) -> str:
    """Request the English version of the given admin page."""
    with translation.override("en"):
        url = reverse(url_name, args=args)
    return client.get(url).content.decode()


def test_word_change_form_warns_at_word_and_unit_word_image(
    admin_client: Client, unit_word: UnitWordRelation
) -> None:
    """The word image field and the unit-word image column both warn."""
    content = get_page(admin_client, "admin:cmsv2_word_change", unit_word.word.pk)

    # help text of the "image" field
    assert f'<div class="help-block">{WARNING_SIGN}' in content
    # "image with controls" column of the unit-word inline
    assert WARNING_SIGN in content.split('id="id_image"')[1]


def test_word_add_form_warns_at_word_image(admin_client: Client) -> None:
    """A new word has no unit-word relations yet, but its image field warns."""
    content = get_page(admin_client, "admin:cmsv2_word_add")

    assert f'<div class="help-block">{WARNING_SIGN}' in content


def test_unit_change_form_warns_at_unit_word_image(
    admin_client: Client, unit_word: UnitWordRelation
) -> None:
    """The word inline on the unit page uploads unit-word images as well."""
    content = get_page(admin_client, "admin:cmsv2_unit_change", unit_word.unit.pk)

    assert WARNING_SIGN in content


@pytest.mark.usefixtures("unit_word")
def test_word_changelist_warns_in_image_column_header(admin_client: Client) -> None:
    """The image column of the word list has upload buttons in every row."""
    content = get_page(admin_client, "admin:cmsv2_word_changelist")

    # only once in the column header, not in every row
    assert content.count(WARNING_SIGN) == 1
