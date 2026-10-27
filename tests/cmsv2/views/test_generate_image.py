from __future__ import annotations

import base64
import re
from collections.abc import Generator
from importlib import import_module
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from lunes_cms.cmsv2.models import (
    AIGeneration,
    Area,
    Job,
    Unit,
    UnitWordRelation,
    Word,
)
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
    client.images.edit.return_value.data = [
        mock.MagicMock(b64_json=base64.b64encode(b"webp").decode())
    ]
    with (
        mock.patch.object(image_generation, "get_openai_client", return_value=client),
        mock.patch.object(generate_image.settings, "TEMP_IMAGE_DIR", str(tmp_path)),
    ):
        yield


def _content(area: Area) -> UnitWordRelation:
    """
    A word in a unit of a job, all in ``area``.
    """
    job = Job.objects.create(name="Tischler/in", area=area)
    unit = Unit.objects.create(title="Werkzeuge", area=area)
    unit.jobs.add(job)
    word = Word.objects.create(word="Hammer", singular_article=1, area=area)
    return UnitWordRelation.objects.create(unit=unit, word=word)


@pytest.mark.django_db
def test_generation_is_recorded_for_the_area_of_the_word(
    client: Client, fake_openai: None
) -> None:
    area = Area.objects.create(name="Testarea")
    user = get_user_model().objects.create_user(
        username="testarea-admin", is_staff=True
    )
    user.user_permissions.add(Permission.objects.get(codename="change_word"))
    area.admins.add(user)
    client.force_login(user)
    word = _content(area).word

    response = client.post(
        reverse("cmsv2:word_generate_image_via_openai", args=[word.pk])
    )

    assert response.status_code == 200
    generation = AIGeneration.objects.get()
    assert generation.generation_event == AIGenerationEvent.IMAGE
    assert generation.area == area


@pytest.mark.django_db
def test_word_endpoint_sends_the_job_and_unit_of_the_word(
    admin_client: Client, fake_openai: None
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]),
            {"additional_info": "mit Holzgriff", "allow_text_in_image": "true"},
        )

    assert image_call.call_args.args[0] == image_generation.build_word_image_prompt(
        word, additional_info="mit Holzgriff", allow_text_in_image=True
    )
    assert "Beruflicher Kontext: Tischler/in." in image_call.call_args.args[0]


@pytest.mark.django_db
def test_unitword_endpoint_uses_the_unit_of_the_relation(
    admin_client: Client, fake_openai: None
) -> None:
    unitword = _content(Area.objects.create(name="Testarea"))
    other_unit = Unit.objects.create(title="Baustelle", area=unitword.unit.area)
    UnitWordRelation.objects.create(unit=other_unit, word=unitword.word)

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        response = admin_client.post(
            reverse("cmsv2:unitword_generate_image_via_openai", args=[unitword.pk])
        )

    assert response.status_code == 200
    assert "Thematischer Kontext: Werkzeuge." in image_call.call_args.args[0]
    assert "Beruflicher Kontext: Tischler/in." in image_call.call_args.args[0]


@pytest.mark.django_db
def test_word_prompt_preview_follows_the_editor_hints(admin_client: Client) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    response = admin_client.post(
        reverse("cmsv2:word_image_prompt_preview", args=[word.pk]),
        {"additional_info": "mit Holzgriff"},
    )

    assert response.json() == {
        "prompt": image_generation.build_word_image_prompt(
            word, additional_info="mit Holzgriff"
        )
    }
    assert not AIGeneration.objects.exists()


@pytest.mark.django_db
def test_unitword_prompt_preview_uses_the_unit_of_the_relation(
    admin_client: Client,
) -> None:
    unitword = _content(Area.objects.create(name="Testarea"))
    other_unit = Unit.objects.create(title="Baustelle", area=unitword.unit.area)
    UnitWordRelation.objects.create(unit=other_unit, word=unitword.word)

    response = admin_client.post(
        reverse("cmsv2:unitword_image_prompt_preview", args=[unitword.pk])
    )

    assert "Thematischer Kontext: Werkzeuge." in response.json()["prompt"]


@pytest.mark.django_db
def test_unitword_page_explains_the_prompt(admin_client: Client) -> None:
    unitword = _content(Area.objects.create(name="Testarea"))

    response = admin_client.get(
        reverse("cmsv2:unitword_generate_image", args=[unitword.pk])
    )

    content = response.content.decode()
    assert 'class="image-prompt-info"' in content
    assert reverse("cmsv2:unitword_image_prompt_preview", args=[unitword.pk]) in content
    assert "Thematischer Kontext: Werkzeuge." in content
    # The generate url block spans several lines after djlint, so it has to
    # end up in a template literal: a "..." string with a newline is a syntax
    # error that leaves the button dead.
    generate_url = reverse(
        "cmsv2:unitword_generate_image_via_openai", args=[unitword.pk]
    )
    assert re.search(
        rf"generateUrl: `\s*{re.escape(generate_url)}\s*`\.trim\(\)", content
    )
