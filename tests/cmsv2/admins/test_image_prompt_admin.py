"""
Tests for the admin of the stored image generation prompts (#1143).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import ImagePrompt
from tests.cmsv2.helpers import PermissionClient

CHANGELIST = "admin:cmsv2_imageprompt_changelist"


@pytest.fixture
def superuser_client(db: None, client: Client) -> Client:
    """
    A client logged in as a superuser.
    """
    client.force_login(
        get_user_model().objects.create_superuser("prompt-admin", password="x")
    )
    return client


def _change_url(prompt: ImagePrompt) -> str:
    return reverse("admin:cmsv2_imageprompt_change", args=[prompt.pk])


def _form_data(instance: ImagePrompt, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": instance.name,
        "prompt": instance.prompt,
        "prompt_with_people": instance.prompt_with_people,
        "prompt_without_people": instance.prompt_without_people,
    }
    for flag in ("supports_show_people", "is_default", "is_active"):
        if getattr(instance, flag):
            data[flag] = "on"
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


@pytest.mark.django_db
def test_editors_cant_see_the_prompts(
    client_with_permissions: Callable[..., PermissionClient],
) -> None:
    editor = client_with_permissions(
        "view_imageprompt", "change_imageprompt", "change_word"
    )

    assert editor.get(reverse(CHANGELIST)).status_code == 403
    assert editor.get(_change_url(ImagePrompt.get_default())).status_code == 403


@pytest.mark.django_db
def test_superusers_can_add_a_prompt(superuser_client: Client) -> None:
    response = superuser_client.post(
        reverse("admin:cmsv2_imageprompt_add"),
        {"name": "Skizze", "prompt": "Eine Skizze: {{ word }}.", "is_active": "on"},
    )

    assert response.status_code == 302
    assert ImagePrompt.objects.get(name="Skizze").render("Hammer") == (
        "Eine Skizze: Hammer."
    )


@pytest.mark.django_db
def test_an_invalid_template_is_shown_as_form_error(superuser_client: Client) -> None:
    response = superuser_client.post(
        reverse("admin:cmsv2_imageprompt_add"),
        {"name": "Kaputt", "prompt": "{% if job %}", "is_active": "on"},
    )

    assert response.status_code == 200
    assert "not a valid template" in response.content.decode()
    assert not ImagePrompt.objects.filter(name="Kaputt").exists()


@pytest.mark.django_db
def test_an_unused_prompt_can_be_edited(superuser_client: Client) -> None:
    prompt = ImagePrompt.get_default()

    response = superuser_client.post(
        _change_url(prompt), _form_data(prompt, prompt="Neu: {{ word }}")
    )

    assert response.status_code == 302
    prompt.refresh_from_db()
    assert prompt.prompt == "Neu: {{ word }}"


@pytest.mark.django_db
def test_the_text_of_a_used_prompt_is_read_only(superuser_client: Client) -> None:
    prompt = ImagePrompt.get_default()
    prompt.mark_used()
    original = prompt.prompt

    page = superuser_client.get(_change_url(prompt)).content.decode()
    response = superuser_client.post(
        _change_url(prompt), _form_data(prompt, prompt="Neu: {{ word }}")
    )

    assert 'name="prompt"' not in page
    assert "can&#x27;t be changed any more" in page
    assert response.status_code == 302
    prompt.refresh_from_db()
    assert prompt.prompt == original


@pytest.mark.django_db
def test_the_default_and_used_prompts_cant_be_deleted(
    superuser_client: Client,
) -> None:
    ImagePrompt.objects.exclude(is_default=True).delete()
    default = ImagePrompt.get_default()
    used = ImagePrompt.objects.create(name="Benutzt", prompt="x")
    used.mark_used()
    unused = ImagePrompt.objects.create(name="Unbenutzt", prompt="x")

    def delete(prompt: ImagePrompt) -> int:
        return superuser_client.post(
            reverse("admin:cmsv2_imageprompt_delete", args=[prompt.pk]),
            {"post": "yes"},
        ).status_code

    assert delete(default) == 403
    assert delete(used) == 403
    assert delete(unused) == 302
    assert set(ImagePrompt.objects.values_list("name", flat=True)) == {
        default.name,
        "Benutzt",
    }


@pytest.mark.django_db
def test_the_bulk_delete_action_is_not_offered(superuser_client: Client) -> None:
    page = superuser_client.get(reverse(CHANGELIST)).content.decode()

    assert "delete_selected" not in page
    assert "copy_prompts" in page


@pytest.mark.django_db
def test_copying_a_single_prompt_opens_the_copy(superuser_client: Client) -> None:
    prompt = ImagePrompt.get_default()

    response = superuser_client.post(
        reverse(CHANGELIST),
        {"action": "copy_prompts", "_selected_action": [prompt.pk]},
    )

    copy = ImagePrompt.objects.get(name=f"Copy of {prompt.name}")
    assert response.status_code == 302
    assert response["Location"] == _change_url(copy)
    assert copy.prompt == prompt.prompt


@pytest.mark.django_db
def test_another_prompt_can_be_made_the_default(superuser_client: Client) -> None:
    previous = ImagePrompt.get_default()
    prompt = ImagePrompt.objects.create(name="Skizze", prompt="Skizze: {{ word }}")

    response = superuser_client.post(
        _change_url(prompt), _form_data(prompt, is_default="on")
    )

    assert response.status_code == 302
    assert ImagePrompt.get_default() == prompt
    previous.refresh_from_db()
    assert not previous.is_default


@pytest.mark.django_db
def test_the_form_loads_the_script_toggling_the_prompt_fields(
    superuser_client: Client,
) -> None:
    page = superuser_client.get(reverse("admin:cmsv2_imageprompt_add")).content.decode()

    assert "js/image_prompt_fields.js" in page
    for field in ("prompt", "prompt_with_people", "prompt_without_people"):
        assert f"field-{field}" in page


@pytest.mark.django_db
@pytest.mark.parametrize(
    "supports_show_people, shown, hidden",
    [
        (False, ["prompt"], ["prompt_with_people", "prompt_without_people"]),
        (True, ["prompt_with_people", "prompt_without_people"], ["prompt"]),
    ],
)
def test_a_used_prompt_shows_only_the_text_it_is_rendered_from(
    superuser_client: Client,
    supports_show_people: bool,
    shown: list[str],
    hidden: list[str],
) -> None:
    prompt = ImagePrompt.objects.create(
        name="Benutzt",
        supports_show_people=supports_show_people,
        prompt="Einzeln",
        prompt_with_people="Mit",
        prompt_without_people="Ohne",
    )
    prompt.mark_used()

    page = superuser_client.get(_change_url(prompt)).content.decode()

    for field in shown:
        assert f"field-{field}" in page
    for field in hidden:
        assert f'field-{field}"' not in page and f"field-{field} " not in page
