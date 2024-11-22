from django.db import models
from django.utils.translation import gettext_lazy as _

from .document import Document
from .static import Static


class AlternativeWord(models.Model):
    """
    Contains alternative words that can be linked to a document
    """

    alt_word = models.CharField(max_length=255, verbose_name=_("alternative word"))
    grammatical_gender = models.IntegerField(
        choices=Static.grammatical_genders,
        verbose_name=_("grammatical gender"),
        blank=True,
        null=True,
    )
    singular_article = models.IntegerField(
        choices=Static.singular_article_choices,
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
        choices=Static.plural_article_choices,
        verbose_name=_("plural article"),
        blank=True,
        null=True,
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="alternatives"
    )

    def __str__(self):
        """String representation of AlternativeWord instance

        :return: title of alternative word instance
        :rtype: str
        """
        return str(self.alt_word)

    # pylint: disable=too-few-public-methods
    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("alternative word")
        verbose_name_plural = _("alternative words")
