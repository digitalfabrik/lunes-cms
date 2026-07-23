"""
Tests for the WordAdminForm's create-time duplicate-check wiring (issue #531).
"""

from __future__ import annotations

import re

import pytest
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.admins.word_admin import WordAdminForm

pytestmark = pytest.mark.django_db


def test_word_field_widget_carries_check_duplicate_url() -> None:
    form = WordAdminForm()
    check_url = form.fields["word"].widget.attrs["data-check-url"]
    assert str(check_url) == reverse("cmsv2:word_check_duplicate")


def test_word_add_page_renders_check_url_and_script(admin_client: Client) -> None:
    response = admin_client.get(reverse("admin:cmsv2_word_add"))

    assert response.status_code == 200
    content = response.content.decode()
    assert f'data-check-url="{reverse("cmsv2:word_check_duplicate")}"' in content
    assert "word_duplicate_check.js" in content


def test_word_field_keeps_same_widget_class_as_other_text_fields(
    admin_client: Client,
) -> None:
    """The data-check-url attribute must not replace the field's normal admin
    widget (issue: the word field lost its full-width vTextField styling)."""
    response = admin_client.get(reverse("admin:cmsv2_word_add"))
    content = response.content.decode()

    word_match = re.search(r'<input[^>]*name="word"[^>]*>', content)
    plural_match = re.search(r'<input[^>]*name="plural"[^>]*>', content)
    assert word_match is not None
    assert plural_match is not None

    assert 'class="vTextField"' in word_match.group(0)
    assert 'class="vTextField"' in plural_match.group(0)
