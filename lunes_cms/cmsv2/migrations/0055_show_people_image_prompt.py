from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import migrations

if TYPE_CHECKING:
    from django.apps.registry import Apps
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor

#: Name of the prompt this migration creates.
PROMPT_NAME = "Prompt mit Personen-Varianten"

#: Name of the prompt migration 0053 created, the default until now.
PREVIOUS_DEFAULT_NAME = "Ursprünglicher Prompt"

#: Shared beginning of both variants: what the image shows and its context.
_SUBJECT = (
    "Ein realistisches, professionelles Foto, das eindeutig zeigt: {{ word }}."
    "{% if job %} Beruflicher Kontext: {{ job }}.{% endif %}"
    "{% if unit %} Thematischer Kontext: {{ unit }}.{% endif %}"
)

#: Shared end of both variants: style and the editor's hints.
_STYLE = (
    " Fotorealistisch, keine Illustration, kein Rendering."
    "{% if additional_info %} Hinweise zur Bildgestaltung: {{ additional_info }}.{% endif %}"
)

#: Variant for words shown with people (#1147). One or two people, and variety
#: across images instead of within each one, so that not every image tries to
#: show every kind of person at once.
PROMPT_WITH_PEOPLE = (
    _SUBJECT + " Eine oder höchstens zwei Personen führen eine typische, natürliche"
    " Handlung aus, die den Begriff verständlich macht, vor einem neutralen weißen"
    " Hintergrund, ohne zusätzliche Objekte. Die Personen wirken wie gewöhnliche"
    " Menschen aus dem Arbeitsalltag in Deutschland; Alter, Geschlecht und Herkunft"
    " dürfen von Bild zu Bild variieren, das Bild wirkt aber nicht inszeniert." + _STYLE
)

#: Variant for words shown without people (#1147). Image models tend to draw
#: people unless told not to, so it excludes them explicitly.
PROMPT_WITHOUT_PEOPLE = (
    _SUBJECT + " Nur das zentrale Motiv ist zu sehen, vor einem neutralen weißen"
    " Hintergrund, ohne zusätzliche Objekte. Es sind keine Menschen, keine Hände und"
    " keine anderen Körperteile zu sehen." + _STYLE
)


def create_show_people_prompt(
    apps: Apps, _schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """
    Create the prompt with show-people variants and make it the default.
    """
    ImagePrompt = apps.get_model("cmsv2", "ImagePrompt")
    ImagePrompt.objects.filter(is_default=True).update(is_default=False)
    ImagePrompt.objects.create(
        name=PROMPT_NAME,
        supports_show_people=True,
        prompt_with_people=PROMPT_WITH_PEOPLE,
        prompt_without_people=PROMPT_WITHOUT_PEOPLE,
        is_default=True,
    )


def remove_show_people_prompt(
    apps: Apps, _schema_editor: BaseDatabaseSchemaEditor
) -> None:
    """
    Make the previous prompt the default again, and remove the prompt this
    migration created unless images have been generated with it.
    """
    ImagePrompt = apps.get_model("cmsv2", "ImagePrompt")
    prompt = ImagePrompt.objects.filter(name=PROMPT_NAME).first()
    if prompt is None or not prompt.is_default:
        return
    previous = ImagePrompt.objects.filter(name=PREVIOUS_DEFAULT_NAME).first()
    if previous is None:
        return
    prompt.is_default = False
    prompt.save(update_fields=["is_default"])
    previous.is_default = True
    previous.is_active = True
    previous.save(update_fields=["is_default", "is_active"])
    if prompt.used_at is None:
        prompt.delete()


class Migration(migrations.Migration):
    """
    Add a prompt with variants for images with and without people and make it
    the default (#1147).
    """

    dependencies = [
        ("cmsv2", "0054_image_generation_record_and_show_people"),
    ]

    operations = [
        migrations.RunPython(create_show_people_prompt, remove_show_people_prompt),
    ]
