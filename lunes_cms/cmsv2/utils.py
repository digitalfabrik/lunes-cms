import logging
import os
import pathlib
import string
import uuid
import warnings
from html import escape

from django.utils.crypto import get_random_string
from django.utils.html import mark_safe
from django.utils.translation import gettext as _
from openai import OpenAI

from lunes_cms.core import settings

logger = logging.getLogger(__name__)


class OpenAIConfigurationError(Exception):
    """Exception raised when OpenAI API is not properly configured."""


def create_resource_path(parent_dir, filename):
    """
    Create a unique path for a resource file.

    Args:
        parent_dir (str): The parent directory for the resource
        filename (str): The original filename

    Returns:
        str: A unique path combining the parent directory and a UUID-based filename
    """
    return os.path.join(parent_dir, str(uuid.uuid1()) + pathlib.Path(filename).suffix)


def get_random_key(length: int = 10, excluded_chars: list = None) -> str:
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


def word_to_string(word):
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


def get_child_count(disc):
    """
    Count the number of released children with training sets.

    Args:
        disc: The parent object whose children will be counted

    Returns:
        int: The count of released children with at least one training set
    """
    children_counter = 0
    for child in disc.get_children():
        if child.released and get_training_set_count(child) > 0:
            children_counter += 1
    return children_counter


def get_training_set_count(disc):
    """
    Count the total number of training sets for an object and its descendants.

    Args:
        disc: The object whose training sets will be counted

    Returns:
        int: The total count of training sets
    """
    training_set_counter = 0
    for child in disc.get_descendants(include_self=True):
        training_set_counter += child.training_sets.count()
    return training_set_counter


def get_image_tag(image, width=330):
    """
    Generate an HTML image tag for the given image.

    Args:
        image: The image object to render
        width (int, optional): The width of the image in pixels. Defaults to 330.

    Returns:
        str: An HTML img tag with the appropriate attributes
    """
    src = ""
    if (
        image
        and image.storage.exists(image.name)
        and any(image.name.lower().endswith(ext) for ext in [".jpg", ".png"])
    ):
        src = escape(f"{settings.MEDIA_URL}{image}")
    html_cls = "" if src else 'class="hidden"'
    return mark_safe(f'<img src="{src}" width={width} height="auto" {html_cls} />')


# pylint: disable=redefined-builtin
def iter_to_string(iter):
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


def get_openai_client():
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


def check_openai_availability():
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


def is_not_blank(s):
    """
    Checks if s is not an empty string.
    """
    return s is not None and s.strip() != ""
