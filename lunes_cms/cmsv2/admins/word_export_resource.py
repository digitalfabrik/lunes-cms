from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionMixin

from ..models import Word
from ..models.static import Static


class WordExportResource(resources.ModelResource):
    """
    Resource to export words from the discipline view.
    """

    # pylint: disable=pointless-statement
    ExportActionMixin.export_admin_action

    # pylint: disable=super-init-not-called
    def __init__(self, for_profession=None):
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

    def dehydrate_singular_article(self, word):
        """
        Method to show the actual singular article and not their integer.
        """
        for x in Static.singular_article_choices:
            if x[0] == word.singular_article:
                return x[1]
        return "-"

    plural_article = fields.Field(
        column_name=_("Plural Article"),
        attribute="plural_article_choices",
    )

    def dehydrate_plural_article(self, word):
        """
        Method to show the actual plural article and not their integer.
        """
        for x in Static.plural_article_choices:
            if x[0] == word.plural_article:
                return x[1]
        return "-"

    has_audio = fields.Field(column_name=_("Has audio?"), attribute="word")

    def dehydrate_has_audio(self, word):
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

    def dehydrate_creation_date(self, word):
        """
        Only show first 16 characters of date (date, and hours & minutes).
        """
        return str(word.creation_date)[:16]

    units = fields.Field(column_name=_("Units"), attribute="units")

    def dehydrate_units(self, word):
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
            "plural_article",
            "has_audio",
            "example_sentence",
            "creation_date",
            "units",
        )
