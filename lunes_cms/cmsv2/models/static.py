import os
from django.db import models
from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from PIL import Image

from ..utils import create_resource_path, make_safe_filename


class UserRole(models.TextChoices):
    """
    List of all user roles.
    """

    ADMIN = ("ADMIN", _("Admins"))
    PARTNERMANAGEMENT = ("PARTNERMANAGEMENT", "Lunes Partnermanagement (v2)")
    VOCABULARYMANAGER = ("VOCABULARYMANAGER", "Lunes Vokabelverwaltung (v2)")


class Static:
    """
    Module for static and global variables
    """

    # Possible articles
    singular_article_choices = [
        (0, "keiner"),
        (1, "der"),
        (2, "die"),
        (3, "das"),
        (4, "die (Plural)"),
    ]
    plural_article_choices = [
        (0, "keiner"),
        (1, "die (Plural)"),
    ]

    # Possible word types
    word_type_choices = [
        ("Nomen", "Substantiv"),
        ("Verb", "Verb"),
        ("Adjektiv", "Adjektiv"),
        ("Numeral", "Numeral"),
        ("Pronomen", "Pronomen"),
        ("Adverb", "Adverb"),
    ]

    # Possible grammatical genders
    grammatical_genders = [
        (0, "kein"),
        (1, "Maskulinum"),
        (2, "Femininum"),
        (3, "Neutrum"),
        (4, "Plural"),
    ]

    # Audio check status choices
    check_status_choices = [
        ("NOT_CHECKED", "Not Checked"),
        ("CONFIRMED", "Confirmed"),
    ]

    # Review status choices
    review_status_choices = [
        ("PENDING", _("Pending Review")),
        ("APPROVED", _("Approved")),
    ]

    # number of pixels used for box blur
    blurr_radius = 30
    # maximum (width, height) of images
    img_size = (1024, 768)

    # super admin group name
    admin_group = "Lunes"
    reviewer_group = _("Reviewer")

    # default group name
    default_group_name = None

    # permissions
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


REVIEW_STATUS_CHOICES = Static.review_status_choices


def convert_image_to_webp(image_field):
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
    new_path = os.path.splitext(old_path)[0] + ".webp"
    new_name = os.path.splitext(old_name)[0] + ".webp"

    if old_path == new_path:
        return False

    img = Image.open(old_path)
    img.save(new_path, format="WEBP", quality=85)
    os.remove(old_path)
    image_field.name = new_name
    return True


def convert_umlaute_images(_, filename):
    """
    Convert file name of images to handle all kind of characters (including "Umlaute" etc.).


    :param filename: name of the file
    :type filename: str

    :return: file path of converted image
    :rtype: str
    """
    return create_resource_path("images", filename)


def convert_umlaute_audio(_, filename):
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


def upload_sponsor_logos(_, filename):
    """
    Upload path for sponsor logos


    :param filename: name of the file
    :type filename: str

    :return: file path for sponsor logos
    :rtype: str
    """
    return create_resource_path("sponsors", filename)


@receiver(post_save, sender=User)
def create_user_profile(instance, created, **_kwargs):
    """
    Automatically adds a group when creating a new user
    if group name given in Static module

    :param instance: user that eventually will be added to a new group
    :type instance: django.contrib.auth.models
    :param created: checks if User is creator
    :type created: bool

    :return: False if User is not creator and not part of Static.default_group_name
    :rtype: bool
    """
    if Static.default_group_name:
        default_group = Group.objects.filter(name=Static.default_group_name)
        if not created or not default_group:
            return False
        instance.groups.add(Group.objects.get(name=Static.default_group_name))
    return True


def is_reviewer(user: User) -> bool:
    """
    Check if the user is a reviewer.
    """
    return user.groups.filter(name=Static.admin_group).exists()


def user_has_role(user: User, *roles: UserRole) -> bool:
    """
    Check if the user has any of the given roles.

    Superusers are always treated as having the Admin role.
    """
    if UserRole.ADMIN in roles and user.is_superuser:
        return True
    return user.groups.filter(name__in=[role.label for role in roles]).exists()
