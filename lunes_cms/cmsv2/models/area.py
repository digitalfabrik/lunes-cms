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

    An area owns its jobs and, transitively, the units and words of those jobs.
    Only the administrators of an area (and superusers) can see and change its
    content. Jobs without an area are main app content and belong to no area.
    """

    name = models.CharField(max_length=255, unique=True, verbose_name=_("area"))
    logo = models.ImageField(
        upload_to=upload_area_logos,
        blank=True,
        verbose_name=_("logo"),
        help_text=_("Shown on landing page."),
    )
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[validate_hex_color],
        verbose_name=_("primary color"),
        help_text=_("A hex color e.g. #000000 for black."),
    )
    secondary_color = models.CharField(
        max_length=7,
        blank=True,
        validators=[validate_hex_color],
        verbose_name=_("secondary color"),
        help_text=_("A hex color e.g. #000000 for black."),
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

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        """
        Meta class for the Area model.
        """

        verbose_name = _("Area")
        verbose_name_plural = _("Areas")
        ordering = ["name"]
