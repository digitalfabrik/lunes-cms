from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from ..utils import get_image_tag
from ..validators import validate_hex_color
from .static import upload_area_logos


class Area(models.Model):
    """
    Model representing a dedicated content area of a part organization.

    An area owns its jobs, units and words, each of which stores its area in
    a foreign key of its own. Only the administrators of an area (and
    superusers) can see and change its content. The main app catalog is the
    one area with ``is_main_app=True``.
    """

    name = models.CharField(max_length=255, unique=True, verbose_name=_("area"))
    logo = models.ImageField(
        upload_to=upload_area_logos,
        blank=True,
        verbose_name=_("logo"),
        help_text=_("The main logo, shown in the center of the header in the app."),
    )
    secondary_logo = models.ImageField(
        upload_to=upload_area_logos,
        blank=True,
        verbose_name=_("secondary logo"),
        help_text=_("A second logo, shown at the side of the header in the app."),
    )
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[validate_hex_color],
        verbose_name=_("primary color"),
        help_text=_(
            "Background color of the header in the app and of the area label on "
            "jobs. A hex color e.g. #000000 for black."
        ),
    )
    learning_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[validate_hex_color],
        verbose_name=_("learning color"),
        help_text=_(
            "Background color of the card to learn words in the app. "
            "A hex color e.g. #000000 for black."
        ),
    )
    training_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[validate_hex_color],
        verbose_name=_("training color"),
        help_text=_(
            "Background color of the card to train words in the app. "
            "A hex color e.g. #000000 for black."
        ),
    )
    additional_information = models.TextField(
        blank=True,
        verbose_name=_("additional information"),
    )
    additional_information_url = models.URLField(
        blank=True,
        verbose_name=_("additional information URL"),
    )
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="administered_areas",
        verbose_name=_("administrators"),
        help_text=_(
            "These users manage the content of this area. They only see jobs, "
            "units and words of the areas they administer."
        ),
    )
    is_main_app = models.BooleanField(
        default=False,
        verbose_name=_("main app"),
        help_text=_("Marks the one area for the main app catalog"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("modified at"))

    def logo_tag(self) -> SafeString:
        """
        Generate a small thumbnail of the area's logo for the admin form.

        Returns:
            SafeString: HTML markup showing the logo, or nothing if there is none
        """
        return get_image_tag(self.logo, width=75)

    logo_tag.short_description = ""  # type: ignore[attr-defined]

    def secondary_logo_tag(self) -> SafeString:
        """
        Generate a small thumbnail of the area's secondary logo for the admin form.

        Returns:
            SafeString: HTML markup showing the secondary logo, or nothing if there is none
        """
        return get_image_tag(self.secondary_logo, width=75)

    secondary_logo_tag.short_description = ""  # type: ignore[attr-defined]

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        """
        Meta class for the Area model.
        """

        verbose_name = _("Area")
        verbose_name_plural = _("Areas")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_main_app"],
                condition=models.Q(is_main_app=True),
                name="unique_main_app_area",
            ),
        ]
