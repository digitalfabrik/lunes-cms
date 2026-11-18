"""
Tests for the stored image generation prompts (#1143).
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError

from lunes_cms.cmsv2.models import ImagePrompt


def _prompt(**overrides: Any) -> ImagePrompt:
    fields: dict[str, Any] = {"name": "Skizze", "prompt": "Eine Skizze: {{ word }}."}
    fields.update(overrides)
    return ImagePrompt.objects.create(**fields)


def _errors(prompt: ImagePrompt) -> dict[str, list[str]]:
    with pytest.raises(ValidationError) as error:
        prompt.full_clean()
    return error.value.message_dict


@pytest.mark.django_db
def test_the_migration_creates_an_unused_default() -> None:
    default = ImagePrompt.get_default()

    assert default.is_active
    assert not default.supports_show_people
    assert not default.is_used


@pytest.mark.django_db
def test_the_migrations_add_an_unused_prompt_with_show_people_variants() -> None:
    prompt = ImagePrompt.objects.get(is_default=False)

    assert prompt.is_active
    assert prompt.supports_show_people
    assert not prompt.is_used
    assert prompt in ImagePrompt.selectable()
    prompt.full_clean()


@pytest.mark.django_db
def test_the_show_people_variants_differ_only_in_the_people() -> None:
    prompt = ImagePrompt.objects.get(supports_show_people=True)
    kwargs: dict[str, Any] = {
        "job": "Tischler/in",
        "unit": "Werkzeuge",
        "additional_info": "von oben",
    }

    with_people = prompt.render("Säge", show_people=True, **kwargs)
    without_people = prompt.render("Säge", show_people=False, **kwargs)

    for text in (with_people, without_people):
        assert text.startswith(
            "Ein realistisches, professionelles Foto, das eindeutig zeigt: Säge."
            " Beruflicher Kontext: Tischler/in. Thematischer Kontext: Werkzeuge."
        )
        assert text.endswith(
            "Fotorealistisch, keine Illustration, kein Rendering."
            " Hinweise zur Bildgestaltung: von oben."
        )
    assert "höchstens zwei Personen" in with_people
    assert "von Bild zu Bild" in with_people
    assert "keine Menschen, keine Hände" in without_people
    assert "Person" not in without_people


@pytest.mark.django_db
def test_render_fills_in_the_variables_without_escaping() -> None:
    prompt = _prompt(
        prompt=(
            "{{ word }}.{% if job %} Beruf: {{ job }}.{% endif %}"
            "{% if unit %} Modul: {{ unit }}.{% endif %}"
            "{% if additional_info %} Hinweis: {{ additional_info }}.{% endif %}"
        )
    )

    assert prompt.render("Säge & Co") == "Säge & Co."
    assert (
        prompt.render(
            "Säge",
            job="Tischler/in",
            unit="Werkzeuge & Maschinen",
            additional_info='mit "Griff" <seitlich>',
        )
        == "Säge. Beruf: Tischler/in. Modul: Werkzeuge & Maschinen."
        ' Hinweis: mit "Griff" <seitlich>.'
    )


@pytest.mark.django_db
def test_render_picks_the_people_variant() -> None:
    prompt = _prompt(
        supports_show_people=True,
        prompt="unused",
        prompt_with_people="Mit Menschen: {{ word }}",
        prompt_without_people="Ohne Menschen: {{ word }}",
    )

    assert prompt.render("Beratung", show_people=True) == "Mit Menschen: Beratung"
    assert prompt.render("Hammer", show_people=False) == "Ohne Menschen: Hammer"
    assert prompt.render("Hammer") == "Ohne Menschen: Hammer"


@pytest.mark.django_db
def test_render_ignores_show_people_for_a_single_prompt() -> None:
    assert _prompt().render("Hammer", show_people=True) == "Eine Skizze: Hammer."


@pytest.mark.django_db
def test_clean_requires_the_fields_of_the_chosen_mode() -> None:
    assert set(_errors(ImagePrompt(name="Leer"))) == {"prompt"}
    assert set(
        _errors(ImagePrompt(name="Leer", supports_show_people=True, prompt="x"))
    ) == {"prompt_with_people", "prompt_without_people"}


@pytest.mark.django_db
def test_clean_rejects_an_invalid_template() -> None:
    errors = _errors(ImagePrompt(name="Kaputt", prompt="{% if job %}{{ job }}"))

    assert "not a valid template" in errors["prompt"][0]


@pytest.mark.django_db
def test_clean_rejects_templates_that_include_files() -> None:
    errors = _errors(ImagePrompt(name="Kaputt", prompt="{% load static %}"))

    assert "not a valid template" in errors["prompt"][0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "text, unknown",
    [
        ("{{ wrod }}", "wrod"),
        ("{{ word }}{% if jbo %} Beruf: {{ job }}.{% endif %}", "jbo"),
        ("{{ word }}{% if job and not unti %}x{% endif %}", "unti"),
        ("{{ word|default:untit }}", "untit"),
        ("{{ word }}{% for part in parts %}{{ part }}{% endfor %}", "parts"),
        ("{{ word }}{% with info=infos %}{{ info }}{% endwith %}", "infos"),
    ],
)
def test_clean_rejects_unknown_variables(text: str, unknown: str) -> None:
    errors = _errors(ImagePrompt(name="Tippfehler", prompt=text))

    assert (
        f"Unknown variables: {unknown}. Available variables: word, job, unit "
        "and additional_info."
    ) in errors["prompt"]


@pytest.mark.django_db
def test_clean_accepts_variables_defined_in_the_template() -> None:
    ImagePrompt(
        name="Schleife",
        prompt=(
            "{{ word }}{% for part in unit %}{{ part }}{{ forloop.counter }}"
            "{% endfor %}{% with info=additional_info %}{{ info }}{% endwith %}"
            "{% if job is not None %}{{ job.upper }}{% endif %}"
        ),
    ).full_clean()


@pytest.mark.django_db
def test_clean_requires_the_word() -> None:
    errors = _errors(ImagePrompt(name="Ohne Wort", prompt="Ein Foto von {{ job }}."))

    assert errors["prompt"] == ["The prompt has to contain the word: {{ word }}"]


@pytest.mark.django_db
def test_clean_checks_the_variables_of_both_people_variants() -> None:
    errors = _errors(
        ImagePrompt(
            name="Varianten",
            supports_show_people=True,
            prompt_with_people="{{ word }} mit {{ leute }}",
            prompt_without_people="Ohne Menschen",
        )
    )

    assert set(errors) == {"prompt_with_people", "prompt_without_people"}


@pytest.mark.django_db
def test_clean_reports_the_lock_together_with_other_errors() -> None:
    default = ImagePrompt.get_default()
    default.mark_used()
    default.is_default = False
    default.prompt = "Geändert: {{ word }}"

    errors = _errors(default)

    assert set(errors) == {NON_FIELD_ERRORS, "is_default"}
    assert "can't be changed any more" in errors[NON_FIELD_ERRORS][0]


@pytest.mark.django_db
def test_making_a_prompt_the_default_replaces_the_previous_default() -> None:
    previous = ImagePrompt.get_default()

    new = _prompt(is_default=True)

    previous.refresh_from_db()
    assert not previous.is_default
    assert ImagePrompt.get_default() == new


@pytest.mark.django_db
def test_the_default_cant_be_unset() -> None:
    default = ImagePrompt.get_default()
    default.is_default = False

    assert "is_default" in _errors(default)


@pytest.mark.django_db
def test_the_default_cant_be_deactivated() -> None:
    default = ImagePrompt.get_default()
    default.is_active = False

    assert "is_active" in _errors(default)
    with pytest.raises(IntegrityError):
        default.save()


@pytest.mark.django_db
def test_the_database_allows_only_one_default() -> None:
    with pytest.raises(IntegrityError):
        ImagePrompt.objects.bulk_create(
            [ImagePrompt(name="Zweiter Standard", prompt="x", is_default=True)]
        )


@pytest.mark.django_db
def test_mark_used_records_only_the_first_use() -> None:
    prompt = _prompt()

    prompt.mark_used()
    first_use = prompt.used_at
    ImagePrompt.objects.get(pk=prompt.pk).mark_used()

    prompt.refresh_from_db()
    assert prompt.is_used
    assert prompt.used_at == first_use


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field, value",
    [
        ("prompt", "Geändert: {{ word }}"),
        ("supports_show_people", True),
        ("prompt_with_people", "Mit Menschen"),
    ],
)
def test_the_text_of_a_used_prompt_is_locked(field: str, value: Any) -> None:
    prompt = _prompt()
    prompt.mark_used()
    setattr(prompt, field, value)

    assert "can't be changed any more" in str(_errors(prompt))


@pytest.mark.django_db
def test_a_used_prompt_can_still_be_deactivated_and_made_default() -> None:
    prompt = _prompt()
    prompt.mark_used()

    prompt.is_active = False
    prompt.full_clean()
    prompt.save()
    prompt.is_active = True
    prompt.is_default = True
    prompt.full_clean()
    prompt.save()

    assert ImagePrompt.get_default() == prompt


@pytest.mark.django_db
def test_copy_creates_an_editable_duplicate_with_a_free_name() -> None:
    original = _prompt(
        supports_show_people=True,
        prompt_with_people="Mit {{ word }}",
        prompt_without_people="Ohne {{ word }}",
        is_default=True,
    )
    original.mark_used()

    first = original.copy()
    second = original.copy()

    assert first.name == "Copy of Skizze"
    assert second.name == "Copy of Skizze (2)"
    assert first.supports_show_people
    assert first.prompt_with_people == "Mit {{ word }}"
    assert first.prompt_without_people == "Ohne {{ word }}"
    assert not first.is_default
    assert first.is_active
    assert not first.is_used


@pytest.mark.django_db
def test_selectable_lists_the_active_prompts_default_first() -> None:
    ImagePrompt.objects.exclude(is_default=True).delete()
    default = ImagePrompt.get_default()
    active = _prompt(name="A aktiv")
    _prompt(name="B inaktiv", is_active=False)

    assert list(ImagePrompt.selectable()) == [default, active]


@pytest.mark.django_db
def test_selected_falls_back_to_the_default() -> None:
    assert ImagePrompt.selected(None) == ImagePrompt.get_default()
    assert ImagePrompt.selected("") == ImagePrompt.get_default()


@pytest.mark.django_db
def test_selected_finds_an_active_prompt() -> None:
    active = _prompt()

    assert ImagePrompt.selected(str(active.pk)) == active


@pytest.mark.django_db
@pytest.mark.parametrize("prompt_id", ["abc", "999999", "inactive"])
def test_selected_rejects_unavailable_prompts(prompt_id: str) -> None:
    if prompt_id == "inactive":
        prompt_id = str(_prompt(is_active=False).pk)

    with pytest.raises(ValueError):
        ImagePrompt.selected(prompt_id)
