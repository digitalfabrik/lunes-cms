"""
The explanation of the image prompt shown next to every image generation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise
    from django.utils.safestring import SafeString

    from ..services.image_generation import ImagePromptContext


def render_image_prompt_info(
    context: ImagePromptContext,
    *,
    preview_url: str | None = None,
    note: _StrOrPromise | None = None,
) -> SafeString:
    """
    Render what goes into the image prompt and a preview of it, as it reads
    without the editor's additional info.

    With ``preview_url`` the preview follows the editor's additional info and
    text option as they type (see ``image_prompt_preview.ts``). ``note`` adds a
    sentence for screens that need more explanation.
    """
    return mark_safe(
        render_to_string(
            "admin/image_prompt_info.html",
            {
                "word": context.word,
                "unit_title": context.unit_title,
                "job_title": context.job_title,
                "prompt": context.prompt(),
                "preview_url": preview_url,
                "note": note,
            },
        )
    )
