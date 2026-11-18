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
from pytest_django import Settings

from lunes_cms.cmsv2.models import (
    AIGeneration,
    Area,
    ImagePrompt,
    Job,
    Unit,
    UnitWordRelation,
    Word,
)
from lunes_cms.cmsv2.models.static import AIGenerationEvent
from lunes_cms.cmsv2.services import image_generation, show_people

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
def test_generating_an_image_locks_the_default_prompt(
    admin_client: Client, fake_openai: None
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    admin_client.post(reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]))

    assert ImagePrompt.get_default().is_used


@pytest.mark.django_db
def test_a_failed_generation_leaves_the_prompt_unlocked(admin_client: Client) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        generate_image, "openai_image_bytes", side_effect=ValueError("boom")
    ):
        response = admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk])
        )

    assert response.status_code == 500
    assert not ImagePrompt.get_default().is_used


@pytest.mark.django_db
def test_the_prompt_preview_leaves_the_prompt_unlocked(admin_client: Client) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    admin_client.post(reverse("cmsv2:word_image_prompt_preview", args=[word.pk]))

    assert not ImagePrompt.get_default().is_used


@pytest.mark.django_db
def test_word_prompt_preview_follows_the_editor_hints(
    admin_client: Client, prompt_without_variants: ImagePrompt
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    response = admin_client.post(
        reverse("cmsv2:word_image_prompt_preview", args=[word.pk]),
        {"additional_info": "mit Holzgriff"},
    )

    assert response.json() == {
        "prompt": image_generation.build_word_image_prompt(
            word, additional_info="mit Holzgriff"
        ),
        "show_people": None,
        "supports_show_people": False,
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


def _people_prompt() -> ImagePrompt:
    """
    Make a prompt with show-people variants that are easy to tell apart the
    default prompt.
    """
    return ImagePrompt.objects.create(
        name="Mit Personen",
        supports_show_people=True,
        prompt_with_people="MIT {{ word }}",
        prompt_without_people="OHNE {{ word }}",
        is_default=True,
    )


@pytest.mark.django_db
def test_the_preview_classifies_an_undecided_word(admin_client: Client) -> None:
    _people_prompt()
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        show_people, "classify_show_people", return_value=True
    ) as classify:
        response = admin_client.post(
            reverse("cmsv2:word_image_prompt_preview", args=[word.pk])
        )

    assert classify.call_count == 1
    assert response.json()["show_people"] is True
    assert response.json()["prompt"].startswith("MIT Hammer")
    word.refresh_from_db()
    assert word.show_people is True


@pytest.mark.django_db
def test_the_preview_follows_the_toggle_without_storing_it(
    admin_client: Client,
) -> None:
    _people_prompt()
    word = _content(Area.objects.create(name="Testarea")).word
    Word.objects.filter(pk=word.pk).update(show_people=True)

    response = admin_client.post(
        reverse("cmsv2:word_image_prompt_preview", args=[word.pk]),
        {"show_people": "false"},
    )

    assert response.json()["prompt"].startswith("OHNE Hammer")
    assert response.json()["show_people"] is False
    word.refresh_from_db()
    assert word.show_people is True
    assert not word.show_people_overridden


@pytest.mark.django_db
def test_the_preview_leaves_the_toggle_undecided_if_classifying_fails(
    admin_client: Client,
) -> None:
    _people_prompt()
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        show_people, "classify_show_people", side_effect=ValueError("bad")
    ):
        response = admin_client.post(
            reverse("cmsv2:word_image_prompt_preview", args=[word.pk])
        )

    assert response.json()["show_people"] is None
    assert response.json()["prompt"].startswith("OHNE Hammer")


@pytest.mark.django_db
def test_generating_stores_the_toggle_of_the_editor(
    admin_client: Client, fake_openai: None
) -> None:
    _people_prompt()
    word = _content(Area.objects.create(name="Testarea")).word
    Word.objects.filter(pk=word.pk).update(show_people=True)

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]),
            {"show_people": "false"},
        )

    assert image_call.call_args.args[0].startswith("OHNE Hammer")
    word.refresh_from_db()
    assert word.show_people is False
    assert word.show_people_overridden


@pytest.mark.django_db
def test_the_unitword_generation_uses_the_decision_of_the_word(
    admin_client: Client, fake_openai: None
) -> None:
    _people_prompt()
    unitword = _content(Area.objects.create(name="Testarea"))
    Word.objects.filter(pk=unitword.word.pk).update(show_people=True)

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        admin_client.post(
            reverse("cmsv2:unitword_generate_image_via_openai", args=[unitword.pk])
        )

    assert image_call.call_args.args[0].startswith("MIT Hammer")


@pytest.mark.django_db
def test_the_toggle_is_ignored_for_a_prompt_without_variants(
    admin_client: Client, fake_openai: None, prompt_without_variants: ImagePrompt
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    admin_client.post(
        reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]),
        {"show_people": "true"},
    )

    word.refresh_from_db()
    assert word.show_people is None
    assert not word.show_people_overridden


@pytest.mark.django_db
def test_generating_records_the_prompt_and_model_next_to_the_temporary_image(
    admin_client: Client, fake_openai: None, settings: Settings
) -> None:
    settings.OPENAI_IMAGE_MODELS = ["image-model"]
    word = _content(Area.objects.create(name="Testarea")).word

    response = admin_client.post(
        reverse("cmsv2:word_generate_image_via_openai", args=[word.pk])
    )

    temp_path = Path(generate_image.settings.TEMP_IMAGE_DIR) / (
        response.json()["temp_image_filename"]
    )
    assert image_generation.read_generation_record(str(temp_path)) == (
        ImagePrompt.get_default(),
        "image-model",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("show_people_value", "toggle"),
    [
        (True, r'class="prompt-show-people"\s+checked\s*>'),
        (False, r'class="prompt-show-people"\s*>'),
        (None, r'class="prompt-show-people"\s+data-undecided\s*>'),
    ],
)
def test_the_unitword_page_shows_the_toggle_for_a_people_prompt(
    admin_client: Client, show_people_value: bool | None, toggle: str
) -> None:
    _people_prompt()
    unitword = _content(Area.objects.create(name="Testarea"))
    Word.objects.filter(pk=unitword.word.pk).update(show_people=show_people_value)

    response = admin_client.get(
        reverse("cmsv2:unitword_generate_image", args=[unitword.pk])
    )

    assert re.search(toggle, response.content.decode())


@pytest.mark.django_db
def test_the_unitword_page_hides_the_toggle_for_a_prompt_without_variants(
    admin_client: Client, prompt_without_variants: ImagePrompt
) -> None:
    """
    The toggle is there, but hidden, so selecting a prompt with variants can
    show it (#1146).
    """
    unitword = _content(Area.objects.create(name="Testarea"))

    response = admin_client.get(
        reverse("cmsv2:unitword_generate_image", args=[unitword.pk])
    )

    assert re.search(
        r'class="image-prompt-show-people-block"\s+hidden\s*>',
        response.content.decode(),
    )


@pytest.mark.django_db
def test_rendering_the_page_never_classifies(admin_client: Client) -> None:
    _people_prompt()
    unitword = _content(Area.objects.create(name="Testarea"))

    with mock.patch.object(show_people, "classify_show_people") as classify:
        admin_client.get(reverse("cmsv2:unitword_generate_image", args=[unitword.pk]))
        response = admin_client.get(
            reverse("admin:cmsv2_word_change", args=[unitword.word.pk])
        )

    classify.assert_not_called()
    assert re.search(
        r'class="prompt-show-people"\s+data-undecided\s*>', response.content.decode()
    )


@pytest.mark.django_db
def test_the_unitword_page_offers_the_models_and_the_active_prompts(
    admin_client: Client, settings: Settings
) -> None:
    settings.OPENAI_IMAGE_MODELS = ["model-a", "model-b"]
    ImagePrompt.objects.create(name="Aktiv", prompt="A {{ word }}")
    ImagePrompt.objects.create(name="Inaktiv", prompt="I {{ word }}", is_active=False)
    unitword = _content(Area.objects.create(name="Testarea"))

    response = admin_client.get(
        reverse("cmsv2:unitword_generate_image", args=[unitword.pk])
    )

    content = response.content.decode()
    assert '<option value="model-a">model-a</option>' in content
    assert '<option value="model-b">model-b</option>' in content
    assert "Aktiv" in content
    assert "Inaktiv" not in content
    default = ImagePrompt.get_default()
    assert re.search(rf'<option value="{default.pk}"\s+selected\s*>', content)


@pytest.mark.django_db
def test_generating_uses_the_selected_prompt_and_model(
    admin_client: Client, fake_openai: None, settings: Settings
) -> None:
    settings.OPENAI_IMAGE_MODELS = ["model-a", "model-b"]
    selected = ImagePrompt.objects.create(name="Gewählt", prompt="GEWÄHLT {{ word }}")
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        response = admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]),
            {"image_prompt": selected.pk, "image_model": "model-b"},
        )

    prompt, _area, model = image_call.call_args.args
    assert prompt.startswith("GEWÄHLT Hammer")
    assert model == "model-b"
    temp_path = Path(generate_image.settings.TEMP_IMAGE_DIR) / (
        response.json()["temp_image_filename"]
    )
    assert image_generation.read_generation_record(str(temp_path)) == (
        selected,
        "model-b",
    )
    selected.refresh_from_db()
    assert selected.is_used
    assert not ImagePrompt.get_default().is_used


@pytest.mark.django_db
def test_generating_without_a_selection_uses_the_first_model(
    admin_client: Client, fake_openai: None, settings: Settings
) -> None:
    settings.OPENAI_IMAGE_MODELS = ["model-a", "model-b"]
    word = _content(Area.objects.create(name="Testarea")).word

    with mock.patch.object(
        generate_image, "openai_image_bytes", return_value=b"webp"
    ) as image_call:
        admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk])
        )

    assert image_call.call_args.args[2] == "model-a"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "selection",
    [
        {"image_model": "unknown-model"},
        {"image_prompt": "not-a-number"},
        {"image_prompt": "999999"},
        {"inactive": True},
    ],
)
def test_generating_rejects_an_unavailable_selection(
    admin_client: Client, fake_openai: None, selection: dict[str, object]
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word
    if selection.pop("inactive", False):
        inactive = ImagePrompt.objects.create(
            name="Inaktiv", prompt="I {{ word }}", is_active=False
        )
        selection["image_prompt"] = inactive.pk

    with mock.patch.object(generate_image, "openai_image_bytes") as image_call:
        response = admin_client.post(
            reverse("cmsv2:word_generate_image_via_openai", args=[word.pk]),
            selection,
        )

    assert response.status_code == 400
    assert "error" in response.json()
    image_call.assert_not_called()


@pytest.mark.django_db
def test_the_preview_follows_the_selected_prompt(admin_client: Client) -> None:
    selected = ImagePrompt.objects.create(
        name="Mit Personen",
        supports_show_people=True,
        prompt_with_people="MIT {{ word }}",
        prompt_without_people="OHNE {{ word }}",
    )
    unitword = _content(Area.objects.create(name="Testarea"))

    with mock.patch.object(show_people, "classify_show_people", return_value=True):
        response = admin_client.post(
            reverse("cmsv2:unitword_image_prompt_preview", args=[unitword.pk]),
            {"image_prompt": selected.pk},
        )

    assert response.json()["prompt"].startswith("MIT Hammer")
    assert response.json()["supports_show_people"] is True


@pytest.mark.django_db
def test_the_preview_reports_a_prompt_without_variants(
    admin_client: Client, prompt_without_variants: ImagePrompt
) -> None:
    word = _content(Area.objects.create(name="Testarea")).word

    response = admin_client.post(
        reverse("cmsv2:word_image_prompt_preview", args=[word.pk])
    )

    assert response.json()["supports_show_people"] is False
    assert response.json()["show_people"] is None


@pytest.mark.django_db
def test_the_preview_rejects_an_inactive_prompt(admin_client: Client) -> None:
    inactive = ImagePrompt.objects.create(
        name="Inaktiv", prompt="I {{ word }}", is_active=False
    )
    word = _content(Area.objects.create(name="Testarea")).word

    response = admin_client.post(
        reverse("cmsv2:word_image_prompt_preview", args=[word.pk]),
        {"image_prompt": inactive.pk},
    )

    assert response.status_code == 400
