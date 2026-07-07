from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionMixin

from ..models import Word
from ..models.static import PluralArticle, SingularArticle

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise


class WordExportResource(resources.ModelResource):
    """
    Resource to export words from the job view.
    """

    # pylint: disable=pointless-statement
    ExportActionMixin.export_admin_action

    # pylint: disable=super-init-not-called
    def __init__(self, for_profession: Any = None) -> None:
        self.for_profession = for_profession
        self.relevant_units = (
            for_profession.get_nested_units() if for_profession else None
        )

    word = fields.Field(column_name=_("Word"), attribute="word")

    word_type = fields.Field(column_name=_("Word type"), attribute="word_type")

    singular_article = fields.Field(
        column_name=_("Singular Article"),
        attribute="singular_article",
    )

    def dehydrate_singular_article(self, word: Word) -> str:
        """
        Method to show the actual singular article and not their integer.
        """
        try:
            return SingularArticle(word.singular_article).label
        except ValueError:
            return "-"

    plural = fields.Field(column_name=_("Plural"), attribute="plural")

    plural_article = fields.Field(
        column_name=_("Plural Article"),
        attribute="plural_article_choices",
    )

    def dehydrate_plural_article(self, word: Word) -> str:
        """
        Method to show the actual plural article and not their integer.
        """
        if word.plural_article is None:
            return "-"
        try:
            return PluralArticle(word.plural_article).label.replace(" (Plural)", "")
        except ValueError:
            return "-"

    has_audio = fields.Field(column_name=_("Has audio?"), attribute="word")

    def dehydrate_has_audio(self, word: Word) -> "_StrOrPromise":
        """
        Returns yes if audio exists and no if it doesn't.
        """
        if word.audio:
            return _("Yes")
        return _("No")

    example_sentence = fields.Field(
        column_name=_("Example sentence"), attribute="example_sentence"
    )

    creation_date = fields.Field(
        column_name=_("Creation date"), attribute="creation_date"
    )

    def dehydrate_creation_date(self, word: Word) -> str:
        """
        Only show first 16 characters of date (date, and hours & minutes).
        """
        return word.creation_date.strftime("%d.%m.%Y %H:%M")

    units = fields.Field(column_name=_("Units"), attribute="units")

    def dehydrate_units(self, word: Word) -> str:
        """
        Method to get relevant units.
        """
        relevant_units = (
            self.relevant_units
            if self.relevant_units
            else word.units.values_list("id", flat=True)
        )
        return " | ".join([t.title for t in word.units.filter(id__in=relevant_units)])

    class Meta:
        """
        Meta class of word resource
        """

        model = Word
        fields = (
            "word",
            "word_type",
            "singular_article",
            "plural",
            "plural_article",
            "has_audio",
            "example_sentence",
            "creation_date",
            "units",
        )
