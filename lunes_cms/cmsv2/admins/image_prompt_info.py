"""
The explanation of the image prompt shown next to every image generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from ..models import ImagePrompt
from ..services.image_generation import image_models

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise
    from django.utils.safestring import SafeString

    from ..models import Word
    from ..services.image_generation import ImagePromptContext


def render_image_prompt_info(  # pylint: disable=too-many-arguments
    context: ImagePromptContext,
    *,
    preview_url: str | None = None,
    note: _StrOrPromise | None = None,
    word: Word | None = None,
    with_selection: bool = True,
    with_additional_info: bool | None = None,
) -> SafeString:
    """
    Render what goes into the image prompt and a preview of it, as it reads
    without the editor's additional info.

    With ``preview_url`` the preview follows the editor's additional info and
    text option as they type (see ``image_prompt_preview.ts``). ``note`` adds a
    sentence for screens that need more explanation. ``with_additional_info``
    points editors to the additional info field; by default, pages with a
    preview have one.

    If the default prompt supports show people, ``word`` adds the toggle
    whether its image shows people, set to its stored decision (#1145). A
    word without a decision shows the variant without people until the
    preview has classified it. Rendering never calls OpenAI.

    ``with_selection`` adds the dropdowns for the model and the prompt, the
    default ones preselected (#1146). The preview and the toggle follow the
    selected prompt. Pages that select them in a form of their own, like the
    CSV import, leave them out and mark their fields with the same classes.
    """
    image_prompt = ImagePrompt.get_default()
    show_people = bool(word is not None and word.show_people)
    return mark_safe(
        render_to_string(
            "admin/image_prompt_info.html",
            {
                "word": context.word,
                "unit_title": context.unit_title,
                "job_title": context.job_title,
                "prompt": context.prompt(
                    image_prompt=image_prompt, show_people=show_people
                ),
                "preview_url": preview_url,
                "note": note,
                "supports_show_people": image_prompt.supports_show_people,
                "show_people_toggle": word is not None,
                "show_people": show_people,
                "show_people_undecided": (
                    word is not None and word.show_people is None
                ),
                "with_selection": with_selection,
                "with_additional_info": (
                    preview_url is not None
                    if with_additional_info is None
                    else with_additional_info
                ),
                "image_models": image_models(),
                "image_prompt": image_prompt,
                "image_prompts": ImagePrompt.selectable() if with_selection else [],
            },
        )
    )
