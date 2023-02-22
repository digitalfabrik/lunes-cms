from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from ..utils import create_resource_path


class Static:
    """
    Module for static and global variables
    """

    # Possible articles
    article_choices = [
        (0, "keiner"),
        (1, "der"),
        (2, "die"),
        (3, "das"),
        (4, "die (Plural)"),
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

    # number of pixels used for box blur
    blurr_radius = 30
    # maximum (width, height) of images
    img_size = (1024, 768)

    # super admin group name
    admin_group = "Lunes"

    # default group name
    default_group_name = None


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
