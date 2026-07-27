"""
Tracks duplicate-vocabulary groups a content manager has explicitly reviewed
and accepted as intentional - e.g. the same word taught with a different
example sentence in a different unit - so they stop showing up in the
"Duplicated vocabulary" analysis section (issue #531).
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from .word import Word


class AcceptedWordDuplicate(models.Model):
    """A duplicate-vocabulary group accepted as intentional."""

    words = models.ManyToManyField(
        Word, related_name="accepted_duplicate_groups", verbose_name=_("words")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        """Meta class for the AcceptedWordDuplicate model."""

        verbose_name = _("accepted word duplicate")
        verbose_name_plural = _("accepted word duplicates")

    def __str__(self) -> str:
        return ", ".join(str(word) for word in self.words.all())
