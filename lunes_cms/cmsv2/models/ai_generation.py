from __future__ import annotations

from typing import Iterable

from django.db import models
from django.utils.translation import gettext_lazy as _

from .area import Area
from .static import AIGenerationEvent


class AIGeneration(models.Model):
    """
    Model recording a single successful request to an AI service.
    """

    areas = models.ManyToManyField(
        Area,
        blank=True,
        related_name="ai_generations",
        verbose_name=_("areas"),
        help_text=_(
            "The areas administered by the user who requested the generation, can be empty."
        ),
    )
    generation_event = models.CharField(
        max_length=32,
        choices=AIGenerationEvent.choices,
        verbose_name=_("generation event"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    def __str__(self) -> str:
        return f"{self.get_generation_event_display()} ({self.created_at})"

    @classmethod
    def record(cls, event: AIGenerationEvent, areas: Iterable[Area]) -> AIGeneration:
        """
        Record a successful AI generation.

        :param event: The kind of content that was generated
        :param areas: The areas the generation is attributed to
        :return: The created record
        """
        generation = cls.objects.create(generation_event=event)
        generation.areas.set(areas)
        return generation

    class Meta:
        """
        Meta class for the AIGeneration model.
        """

        verbose_name = _("AI generation")
        verbose_name_plural = _("AI generations")
        ordering = ["-created_at"]
