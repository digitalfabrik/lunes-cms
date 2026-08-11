"""
Tracks duplicate-vocabulary groups a content manager has explicitly reviewed
and accepted as intentional - e.g. the same word taught with a different
example sentence in a different unit - so they stop showing up in the
"Open duplicates" analysis section (issue #531).
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
        """
        Every ``Word`` here shares the same text by definition - that's
        what makes them duplicates - so show it once, with its article,
        rather than repeating e.g. "(der) X, (der) X" for each underlying
        row (issue #531).
        """
        words = list(self.words.order_by("pk"))
        if not words:
            return ""
        texts = {word.word for word in words}
        if len(texts) == 1:
            return f"({words[0].get_singular_article_display()}) {words[0].word}"
        # Not expected in practice - accepted groups are always same-text -
        # but fall back to listing everything rather than silently hiding
        # a mismatch.
        return ", ".join(str(word) for word in words)
