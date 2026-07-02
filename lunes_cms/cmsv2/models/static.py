from __future__ import annotations

import os
from typing import Any

from django.contrib.auth.models import Group, User
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from PIL import Image

from ..utils import create_resource_path, make_safe_filename


class SingularArticle(models.IntegerChoices):
    """Possible singular articles"""

    NONE = 0, "keiner"
    DER = 1, "der"
    DIE = 2, "die"
    DAS = 3, "das"
    DIE_PLURAL = 4, "die (Plural)"


class PluralArticle(models.IntegerChoices):
    """Possible plural articles"""

    NONE = 0, "keiner"
    DIE_PLURAL = 1, "die (Plural)"


class WordType(models.TextChoices):
    """Possible word types"""

    NOUN = "Nomen", "Substantiv"
    VERB = "Verb", "Verb"
    ADJECTIVE = "Adjektiv", "Adjektiv"
    NUMERAL = "Numeral", "Numeral"
    PRONOUN = "Pronomen", "Pronomen"
    ADVERB = "Adverb", "Adverb"


class GrammaticalGenders(models.IntegerChoices):
    """Possible grammatical genders"""

    NONE = 0, "kein"
    MASCULINUM = 1, "Maskulinum"
    FEMININUM = 2, "Femininum"
    NEUTRUM = 3, "Neutrum"
    PLURAL = 4, "Plural"


class CheckStatus(models.TextChoices):
    """Possible states for unchecked/checked audios and images"""

    CONFIRMED = "CONFIRMED", _("Confirmed")
    NOT_CHECKED = "NOT_CHECKED", _("Not Checked")


class ReviewStatus(models.TextChoices):
    """Possible states for reviews"""

    PENDING = "PENDING", _("Pending Review")
    APPROVED = "APPROVED", _("Approved")


class Roles:
    """Possible user roles"""

    DEFAULT_GROUP_NAME = None
    ADMIN_GROUP = "Lunes"
    REVIEWER_GROUP = _("Reviewer")


class Permissions:
    """Possible permissions"""

    STAFF_PERMISSIONS = [
        "add_job",
        "change_job",
        "delete_job",
        "view_job",
        "add_word",
        "change_word",
        "delete_word",
        "view_word",
        "add_unit",
        "change_unit",
        "delete_unit",
        "view_unit",
        "add_image",
        "change_image",
        "delete_image",
        "view_image",
        "add_feedback",
        "change_feedback",
        "delete_feedback",
        "view_feedback",
        "add_unitwordrelation",
        "change_unitwordrelation",
        "delete_unitwordrelation",
        "view_unitwordrelation",
    ]
    REVIEW_PERMISSIONS = [
        "add_imagereview",
        "change_imagereview",
        "delete_imagereview",
        "view_imagereview",
        "add_reviewassignment",
        "change_reviewassignment",
        "delete_reviewassignment",
        "view_reviewassignment",
    ]


def convert_image_to_webp(image_field: ImageFieldFile) -> bool:
    """
    Converts an ImageField's file to WebP format in-place.

    Opens the existing file, saves it as WebP with quality=85, removes the
    original file if the extension changed, and updates image_field.name.

    :param image_field: An ImageField (FieldFile) whose file is already saved to disk.
    :type image_field: django.db.models.fields.files.FieldFile

    :return: True if the file was converted and renamed, False if already WebP.
    :rtype: bool
    """
    if not image_field:
        return False

    old_path = image_field.path
    old_name = image_field.name
    # `image_field` was truthy above, and FieldFile.__bool__ is defined as
    # bool(self.name), so the name is guaranteed to be a non-empty string here.
    assert old_name is not None
    new_path = os.path.splitext(old_path)[0] + ".webp"
    new_name = os.path.splitext(old_name)[0] + ".webp"

    if old_path == new_path:
        return False

    img = Image.open(old_path)
    img.save(new_path, format="WEBP", quality=85)
    os.remove(old_path)
    image_field.name = new_name
    return True


def convert_umlaute_images(_: models.Model, filename: str) -> str:
    """
    Convert file name of images to handle all kind of characters (including "Umlaute" etc.).


    :param filename: name of the file
    :type filename: str

    :return: file path of converted image
    :rtype: str
    """
    return create_resource_path("images", filename)


def convert_umlaute_audio(_: models.Model, filename: str) -> str:
    """
    Convert file name of audios to handle all kind of
    characters (including "Umlaute" etc.).

    :param filename: name of the file
    :type filename: str

    :return: file path of converted audio
    :rtype: str
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    # convert_audio() re-saves the file as "<name>-conv.mp3"; keep the base name.
    if stem.endswith("-conv"):
        stem = stem[: -len("-conv")]
    safe_stem = make_safe_filename(stem) or "audio"
    return os.path.join("audio", f"{safe_stem}.mp3")


def upload_sponsor_logos(_: models.Model, filename: str) -> str:
    """
    Upload path for sponsor logos


    :param filename: name of the file
    :type filename: str

    :return: file path for sponsor logos
    :rtype: str
    """
    return create_resource_path("sponsors", filename)


@receiver(post_save, sender=User)
def create_user_profile(instance: User, created: bool, **_kwargs: Any) -> bool:
    """
    Automatically adds a group when creating a new user
    if group name given in Roles.DEFAULT_GROUP_NAME

    :param instance: user that eventually will be added to a new group
    :type instance: django.contrib.auth.models
    :param created: checks if User is creator
    :type created: bool

    :return: False if User is not creator and not part of Roles.DEFAULT_GROUP_NAME
    :rtype: bool
    """
    if Roles.DEFAULT_GROUP_NAME:
        default_group = Group.objects.filter(name=Roles.DEFAULT_GROUP_NAME)
        if not created or not default_group:
            return False
        instance.groups.add(Group.objects.get(name=Roles.DEFAULT_GROUP_NAME))
    return True


def is_reviewer(user: User) -> bool:
    """
    Check if the user is a reviewer.
    """
    return user.groups.filter(name=Roles.ADMIN_GROUP).exists()
