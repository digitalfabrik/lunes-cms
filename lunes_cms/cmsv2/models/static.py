import os

from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from PIL import Image

from ..utils import create_resource_path


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

    # default group name
    default_group_name = None


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


def convert_umlaute_images(instance, filename):
    """
    Convert file name of images to handle all kind of characters (including "Umlaute" etc.).


    :param instance: instance where the current file is being attached
    :type instance: django.db.models
    :param filename: name of the file
    :type filename: str

    :return: file path of converted image
    :rtype: str
    """
    return create_resource_path("images", filename)


def convert_umlaute_audio(instance, filename):
    """
    Convert file name of audios to handle all kind of
    characters (including "Umlaute" etc.).

    :param instance: instance where the current file is being attached
    :type instance: django.db.models
    :param filename: name of the file
    :type filename: str

    :return: file path of converted audio
    :rtype: str
    """
    return create_resource_path("audio", filename)


def upload_sponsor_logos(instance, filename):
    """
    Upload path for sponsor logos

    :param instance: instance where the current file is being attached
    :type instance: django.db.models

    :param filename: name of the file
    :type filename: str

    :return: file path for sponsor logos
    :rtype: str
    """
    return create_resource_path("sponsors", filename)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically adds a group when creating a new user
    if group name given in Static module

    :param sender: user that sends request
    :type sender: django.contrib.auth.models
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
