from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
import os


def validate_file_extension(value):
    """
    Function to validate the audio file format

    :param value: audio file returned by a `models.FileField`
    :type value: audio file

    :return: None
    :rtype: None
    """
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [".mp3", ".aac", ".wav", ".m4a", ".wma", ".ogg"]
    if not ext.lower() in valid_extensions:
        raise ValidationError(
            _("File type not supported! Use: .mp3 .aac .wav .m4a .wma .ogg")
        )


def validate_file_size(value):
    """
    Function to validate the size of an audio file

    :param value: audio file returned by a `models.FileField`
    :type value: audio file

    :return: None
    :rtype: None
    """
    if value.size > (5 * 1024 * 1024):
        raise ValidationError(_("File too large! Max. 5 MB"))


def validate_multiple_extensions(value):
    """
    Function that checks if an audio file has multiple extensions

    :param value: audio file returned by a `models.FileField`
    :type value: audio file

    :return: None
    :rtype: None
    """
    split_name = value.name.split(".")
    if len(split_name) != 2:
        raise ValidationError(_("Only use one file extension!"))
