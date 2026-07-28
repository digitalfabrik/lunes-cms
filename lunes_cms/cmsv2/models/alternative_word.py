from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from .static import GrammaticalGenders, PluralArticle, SingularArticle
from .word import Word


class AlternativeWord(models.Model):
    """
    Contains alternative words that can be linked to a word
    """

    alt_word = models.CharField(max_length=255, verbose_name=_("alternative word"))
    grammatical_gender = models.IntegerField(
        choices=GrammaticalGenders.choices,
        verbose_name=_("Grammatical gender"),
        blank=True,
        null=True,
    )
    singular_article = models.IntegerField(
        choices=SingularArticle.choices,
        blank=True,
        null=True,
        verbose_name=_("singular article"),
    )
    plural = models.CharField(
        max_length=255,
        verbose_name=_("plural"),
        blank=True,
        default="",
    )
    plural_article = models.IntegerField(
        choices=PluralArticle.choices,
        verbose_name=_("plural article"),
        blank=True,
        null=True,
    )
    word = models.ForeignKey(
        Word,
        on_delete=models.CASCADE,
        related_name="alternative_words",
        verbose_name=_("word"),
    )

    @property
    def singular_article_as_text(self) -> str:
        """
        Returns:
            str: The singular article of this alternative word as text
        """
        if self.singular_article is None:
            return ""
        return SingularArticle(self.singular_article).label

    def __str__(self) -> str:
        """
        Returns a string representation of the AlternativeWord instance.

        Returns:
            str: The alternative word itself.
        """
        return str(self.alt_word)

    class Meta:
        """
        Meta options for the AlternativeWord model.
        """

        verbose_name = _("alternative word")
        verbose_name_plural = _("alternative words")
