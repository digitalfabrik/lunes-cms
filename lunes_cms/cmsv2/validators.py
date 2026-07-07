from __future__ import annotations

import os

from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.utils.translation import gettext_lazy as _


def validate_file_extension(value: File) -> None:
    """
    Validate that the file has an allowed audio file extension.

    Args:
        value: The file to validate

    Raises:
        ValidationError: If the file extension is not in the list of valid extensions
    """
    ext = os.path.splitext(value.name or "")[1]  # [0] returns path+filename
    valid_extensions = [".mp3", ".aac", ".wav", ".m4a", ".wma", ".ogg"]
    if not ext.lower() in valid_extensions:
        raise ValidationError(
            _("File type not supported! Use: .mp3 .aac .wav .m4a .wma .ogg")
        )


def validate_file_size(value: File) -> None:
    """
    Validate that the file size is within the allowed limit.

    Args:
        value: The file to validate

    Raises:
        ValidationError: If the file size exceeds 5 MB
    """
    if value.size > (5 * 1024 * 1024):
        raise ValidationError(_("File too large! Max. 5 MB"))


def validate_multiple_extensions(value: File) -> None:
    """
    Validate that the file has only one extension.

    Args:
        value: The file to validate

    Raises:
        ValidationError: If the filename contains multiple dots, indicating multiple extensions
    """
    split_name = (value.name or "").split(".")
    if len(split_name) != 2:
        raise ValidationError(_("Only use one file extension!"))
