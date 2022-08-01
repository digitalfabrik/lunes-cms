from django.db import models
from django.utils.translation import ugettext_lazy as _

from .static import Static
from .document import Document


class AlternativeWord(models.Model):
    """
    Contains alternative words that can be linked to a document
    """

    alt_word = models.CharField(max_length=255, verbose_name=_("alternative word"))
    article = models.IntegerField(
        choices=Static.article_choices,
        default="",
        verbose_name=_("article"),
    )
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="alternatives"
    )

    def __str__(self):
        """String representation of AlternativeWord instance

        :return: title of alternative word instance
        :rtype: str
        """
        return self.alt_word

    # pylint: disable=R0903
    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("alternative word")
        verbose_name_plural = _("alternative words")
