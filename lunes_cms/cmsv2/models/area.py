from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Area(models.Model):
    """
    Model representing a dedicated content area of a part organization.

    An area owns its jobs and, transitively, the units and words of those jobs.
    Only the administrators of an area (and superusers) can see and change its
    content. Jobs without an area are main app content and belong to no area.
    """

    name = models.CharField(max_length=255, unique=True, verbose_name=_("area"))
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

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        """
        Meta class for the Area model.
        """

        verbose_name = _("Area")
        verbose_name_plural = _("Areas")
        ordering = ["name"]
