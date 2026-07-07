from __future__ import annotations

import logging
import os
import pathlib
import re
import string
import uuid
import warnings
from html import escape
from typing import Any, Iterable, Optional, TYPE_CHECKING

from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.http import HttpRequest
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext as _
from openai import OpenAI

from lunes_cms.core import settings

if TYPE_CHECKING:
    from lunes_cms.cmsv2.models.word import Word

logger = logging.getLogger(__name__)


class OpenAIConfigurationError(Exception):
    """Exception raised when OpenAI API is not properly configured."""


def create_resource_path(parent_dir: str, filename: str) -> str:
    """
    Create a unique path for a resource file.

    Args:
        parent_dir (str): The parent directory for the resource
        filename (str): The original filename

    Returns:
        str: A unique path combining the parent directory and a UUID-based filename
    """
    return os.path.join(parent_dir, str(uuid.uuid1()) + pathlib.Path(filename).suffix)


def get_random_key(length: int = 10, excluded_chars: Optional[list[str]] = None) -> str:
    """
    Generate a random string key of specified length.

    Args:
        length (int, optional): Length of the key. Defaults to 10.
        excluded_chars (list, optional): Characters to exclude from the key. Defaults to None.

    Returns:
        str: A random string key
    """
    if excluded_chars is None:
        excluded_chars = []
    choices = string.ascii_letters + string.digits
    for char in excluded_chars:
        choices = choices.replace(str(char), "")
    key = get_random_string(length, choices)
    return key


def word_to_string(word: Word) -> str:
    """
    Convert a word object to a formatted string representation.

    Args:
        word: The word object to convert

    Returns:
        str: A string representation of the word with an icon indicating if it has an image
    """
    has_foto_icon = "\U0001f4f7" if word.image else "\U000026a0"
    return (
        has_foto_icon
        + " "
        + "("
        + word.get_singular_article_display()
        + ") "
        + word.word
    )


def cache_busted_url(file: FieldFile) -> str:
    """
    Return a media file's URL with a ?v= query that changes when the file does.

    Regenerated audio is always re-saved under the same deterministic filename
    (e.g. <word>.mp3), so its URL never changes when the content does — and
    browsers keep playing the cached copy. Appending the file's modification
    time makes the URL change on each regeneration, forcing a refetch. Falls
    back to the plain URL if the storage can't report a modification time.

    Args:
        file: A Django FieldFile (e.g. word.audio).

    Returns:
        str: The file URL, cache-busted when possible.
    """
    try:
        version = int(file.storage.get_modified_time(file.name or "").timestamp())
    except (NotImplementedError, OSError, ValueError):
        return file.url
    return f"{file.url}?v={version}"


def get_image_tag(image: ImageFieldFile, width: int = 330) -> SafeString:
    """
    Generate an HTML image tag for the given image.

    Args:
        image: The image object to render
        width: The width of the image in pixels. Defaults to 330.

    Returns:
        SafeString (str): An HTML img tag with the appropriate attributes
    """
    src = ""
    if (
        image
        and image.name
        and image.storage.exists(image.name)
        and any(image.name.lower().endswith(ext) for ext in [".jpg", ".png", ".webp"])
    ):
        src = escape(f"{settings.MEDIA_URL}{image}")
    html_cls = "" if src else 'class="hidden"'
    return mark_safe(f'<img src="{src}" width={int(width)} height="auto" {html_cls} />')


# pylint: disable=redefined-builtin
def iter_to_string(iter: Iterable[Any]) -> str:
    """
    Convert an iterable to a formatted string with quotes and conjunctions.

    Args:
        iter: The iterable to convert to a string

    Returns:
        str: A formatted string representation of the iterable
    """
    lst = list(iter)
    last_element = lst.pop() if len(lst) > 1 else None
    list_str = '"' + '", "'.join(map(str, lst)) + '"'
    if last_element:
        list_str += " " + _("and") + f' "{last_element}"'
    return list_str


def get_openai_client() -> OpenAI:
    """
    Get OpenAI client if API key is available.

    Returns:
        OpenAI client instance if API key is available.

    Raises:
        OpenAIConfigurationError: If OpenAI API key is not configured.
    """
    if not settings.OPENAI_API_KEY:
        raise OpenAIConfigurationError(
            "OpenAI API key is not configured. Set the LUNES_CMS_OPENAI_API_KEY environment variable."
        )

    return OpenAI(api_key=settings.OPENAI_API_KEY)


def check_openai_availability() -> bool:
    """
    Check if OpenAI functionality is available and issue warnings if not.

    This function should be called during app startup to warn about missing configuration.
    """
    if not settings.OPENAI_API_KEY:
        warning_message = (
            "OpenAI API key is not configured. Image and audio generation features will be disabled. "
            "Set the LUNES_CMS_OPENAI_API_KEY environment variable to enable these features."
        )
        warnings.warn(warning_message, UserWarning)
        logger.warning(warning_message)
        return False
    return True


def is_not_blank(s: Optional[str]) -> bool:
    """
    Checks if s is not an empty string.
    """
    return s is not None and s.strip() != ""


def make_safe_filename(unsafe: str) -> str:
    """
    Method to create a safe filename with regex.
    """
    return re.sub(r"[^a-zA-Z0-9.äöüÄÖÜ]+", "_", unsafe)


def is_ajax(request: HttpRequest) -> bool:
    """
    Checks whether the given request was sent via an AJAX call (fetch/XHR).
    """
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def example_sentence_generate_html(
    generate_url: str, store_url: str, target: Optional[str] = None
) -> SafeString:
    """
    Render the inline example sentence generation widget.

    The widget generates a sentence via OpenAI, shows it for review and lets the
    user keep it (persisted right away, like the audio and image widgets) or
    discard it, all without leaving the change page.

    :param generate_url: URL of the AJAX endpoint generating the sentence
    :param store_url: URL of the AJAX endpoint persisting the kept sentence
    :param target: optional id of the textarea to fill (inline rows resolve it
                   from the surrounding table row instead)
    """
    target_attr = format_html(' data-target="{}"', target) if target else ""
    return format_html(
        '<div class="generate-example-sentence">'
        '<button type="button" class="btn btn-primary btn-sm generate-example-sentence-btn" '
        'data-url="{generate_url}" data-store-url="{store_url}"{target_attr} '
        'data-generate-label="{generate_label}" data-regenerate-label="{regenerate_label}">'
        "{generate_label}</button>"
        '<span class="generate-example-sentence-spinner spinner-border spinner-border-sm is-hidden">'
        "</span>"
        '<span class="generate-example-sentence-message"></span>'
        '<div class="generate-example-sentence-decision is-hidden">'
        '<div class="regen-col-label">{new_label}</div>'
        '<div class="generate-example-sentence-preview"></div>'
        '<button type="button" class="btn btn-success btn-sm generate-example-sentence-keep-btn">'
        "{keep_label}</button> "
        '<button type="button" class="btn btn-secondary btn-sm generate-example-sentence-discard-btn">'
        "{discard_label}</button>"
        "</div></div>",
        generate_url=generate_url,
        store_url=store_url,
        target_attr=target_attr,
        generate_label=_("Generate example sentence"),
        regenerate_label=_("Regenerate example sentence"),
        new_label=_("New"),
        keep_label=_("Keep new"),
        discard_label=_("Discard new"),
    )
