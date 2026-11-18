"""
Deciding per word whether its generated images show people (#1145).

An image prompt that supports show people has a variant with and one without
people. Which one a word gets is decided once by a small text model and stored
on the word (``Word.show_people``); editors can change it afterwards. Image
models tend to draw people as soon as a prompt mentions them at all, so the
decision is made before the prompt is built instead of inside it.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from django.conf import settings
from openai import OpenAIError

from ..models import Word
from ..utils import get_openai_client, OpenAIConfigurationError

if TYPE_CHECKING:
    from openai.types.shared_params import ResponseFormatJSONSchema

    from ..models import ImagePrompt
    from .image_generation import ImagePromptContext

logger = logging.getLogger(__name__)

#: Instruction for the classifier. The word and its context follow in a
#: separate message.
CLASSIFIER_INSTRUCTION = (
    "Du hilfst dabei, Bilder für eine Vokabel-Lern-App für berufsbezogenes "
    "Deutsch zu erstellen. Zu jedem Begriff wird ein realistisches Foto "
    "generiert. Entscheide, ob auf dem Foto Menschen zu sehen sein sollen.\n"
    "Zeige Menschen nur, wenn der Begriff ohne sie nicht verständlich "
    "dargestellt werden kann: Tätigkeiten und Handlungen (z. B. Beratung, "
    "Mittagsschlaf, heben), Berufe, Rollen und Personen (z. B. Kundin, "
    "Auszubildender), Körperteile, Körperhaltungen und Gefühle sowie "
    "Interaktionen zwischen Menschen.\n"
    "Zeige keine Menschen bei Gegenständen, Werkzeugen, Geräten, Materialien, "
    "Lebensmitteln, Orten, Gebäuden, Räumen, Fahrzeugen, Tieren, Pflanzen, "
    "Zahlen, Mengen, Formen, Farben, Dokumenten und abstrakten Begriffen, die "
    "sich ohne Menschen darstellen lassen.\n"
    'Antworte im JSON-Format: {"show_people": true} oder '
    '{"show_people": false}.'
)

#: Structured output the classifier has to answer with.
CLASSIFIER_RESPONSE_FORMAT: ResponseFormatJSONSchema = {
    "type": "json_schema",
    "json_schema": {
        "name": "show_people_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"show_people": {"type": "boolean"}},
            "required": ["show_people"],
            "additionalProperties": False,
        },
    },
}


def classifier_input(context: ImagePromptContext) -> str:
    """
    The message telling the classifier which word to decide on, with the job
    and unit it is shown in when the image prompt names them too.
    """
    lines = [f"Begriff: {context.word}"]
    if context.job_title:
        lines.append(f"Beruf: {context.job_title}")
    if context.unit_title:
        lines.append(f"Lerneinheit: {context.unit_title}")
    return "\n".join(lines)


def classify_show_people(context: ImagePromptContext) -> bool:
    """
    Ask the classifier model whether images of the word in ``context`` should
    show people.

    Raises:
        OpenAIConfigurationError: If no OpenAI API key is configured
        OpenAIError: If the request fails
        ValueError: If the answer isn't the expected JSON
    """
    response = get_openai_client().chat.completions.create(
        model=settings.OPENAI_CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFIER_INSTRUCTION},
            {"role": "user", "content": classifier_input(context)},
        ],
        response_format=CLASSIFIER_RESPONSE_FORMAT,
    )
    content = response.choices[0].message.content or ""
    try:
        decision = json.loads(content)["show_people"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError(f"Unexpected classifier answer: {content!r}") from error
    if not isinstance(decision, bool):
        raise ValueError(f"Unexpected classifier answer: {content!r}")
    return decision


def resolve_show_people(
    word: Word, image_prompt: ImagePrompt, context: ImagePromptContext
) -> bool:
    """
    Whether the image of ``word`` generated from ``image_prompt`` shows
    people.

    Prompts without show-people variants never need the decision. Otherwise
    the stored decision is used, and a word without one is classified once and
    the result stored. If classifying fails, the word gets the variant without
    people and nothing is stored, so the next generation tries again.

    The classifier is an OpenAI call, so this must not run inside a
    transaction.
    """
    if not image_prompt.supports_show_people:
        return False
    if word.show_people is not None:
        return word.show_people
    try:
        decision = classify_show_people(context)
    except (OpenAIConfigurationError, OpenAIError, ValueError) as error:
        logger.warning(
            "Deciding whether to show people failed for word_id=%s, using the "
            "variant without people: %s",
            word.pk,
            error,
        )
        return False
    # Only fill in a missing decision: an editor may have set it meanwhile.
    Word.objects.filter(pk=word.pk, show_people__isnull=True).update(
        show_people=decision
    )
    word.show_people = decision
    logger.info("Decided show_people=%s for word_id=%s", decision, word.pk)
    return decision


def set_show_people(word: Word, show_people: bool) -> None:
    """
    Store an editor's decision whether images of ``word`` show people. It is
    marked as set by an editor only if it differs from the stored one.
    """
    if word.show_people == show_people:
        return
    Word.objects.filter(pk=word.pk).update(
        show_people=show_people, show_people_overridden=True
    )
    word.show_people = show_people
    word.show_people_overridden = True
