from __future__ import annotations

from string import ascii_uppercase, digits

from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from .area import Area

#: The characters a code is made of. The letter "O" is left out, because it is
#: easily confused with the digit zero when a code is read out or typed off.
CODE_CHARS = digits + ascii_uppercase.replace("O", "")

#: The length of a generated code. The minimum length of a code is 8, generated
#: ones are longer to leave room for guessing.
GENERATED_CODE_LENGTH = 12


def generate_default_code() -> str:
    """
    Generate a random code of upper case letters and digits.

    :return: A code that can be handed out
    """
    return get_random_string(length=GENERATED_CODE_LENGTH, allowed_chars=CODE_CHARS)


class AreaCode(models.Model):
    """
    Model representing a code that grants access to the content of an area.

    An area can have any number of codes, so that a part organization can hand
    out a separate one per course, cooperation or campaign and withdraw it
    again without affecting the others.
    """

    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="codes",
        verbose_name=_("area"),
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        default=generate_default_code,
        verbose_name=_("code"),
        help_text=_(
            "At least 8 characters, only digits and upper case letters allowed."
        ),
        validators=[
            MinLengthValidator(8),
            RegexValidator(
                r"^[0-9A-Z]*$", _("Only digits and upper case letters allowed")
            ),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("modified at"))

    def __str__(self) -> str:
        return str(self.code)

    class Meta:
        """
        Meta class for the AreaCode model.
        """

        verbose_name = _("Area code")
        verbose_name_plural = _("Area codes")
        ordering = ["code"]
