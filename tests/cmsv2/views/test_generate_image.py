from __future__ import annotations

import base64
from collections.abc import Generator
from importlib import import_module
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import AIGeneration, Area
from lunes_cms.cmsv2.models.static import AIGenerationEvent
from lunes_cms.cmsv2.services import image_generation

# Imported via ``import_module`` so the patch targets the module, whatever
# ``lunes_cms.cmsv2.views`` re-exports under the same name.
generate_image = import_module("lunes_cms.cmsv2.views.generate_image")


@pytest.fixture
def fake_openai(tmp_path: Path) -> Generator[None, None, None]:
    """
    Answer the image request without OpenAI and keep the temporary file out
    of the real media directory.
    """
    client = mock.MagicMock()
    client.images.generate.return_value.data = [
        mock.MagicMock(b64_json=base64.b64encode(b"webp").decode())
    ]
    with (
        mock.patch.object(image_generation, "get_openai_client", return_value=client),
        mock.patch.object(generate_image.settings, "TEMP_IMAGE_DIR", str(tmp_path)),
    ):
        yield


def _generate(client: Client) -> None:
    response = client.post(
        reverse("cmsv2:generate_image_via_openai"), {"word_text": "Hammer"}
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_generation_is_recorded_for_the_areas_of_the_user(
    client: Client, fake_openai: None
) -> None:
    areas = [Area.objects.create(name="Kolping"), Area.objects.create(name="Caritas")]
    Area.objects.create(name="Diakonie")
    user = get_user_model().objects.create_user(username="kolping", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_word"))
    for area in areas:
        area.admins.add(user)
    client.force_login(user)

    _generate(client)

    generation = AIGeneration.objects.get()
    assert generation.generation_event == AIGenerationEvent.IMAGE
    assert set(generation.areas.all()) == set(areas)


@pytest.mark.django_db
def test_generation_of_a_main_app_user_has_no_areas(
    admin_client: Client, fake_openai: None
) -> None:
    Area.objects.create(name="Kolping")

    _generate(admin_client)

    generation = AIGeneration.objects.get()
    assert not generation.areas.exists()
