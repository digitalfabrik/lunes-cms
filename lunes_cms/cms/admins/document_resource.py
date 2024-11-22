from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionMixin

from ..models import Document
from ..models.static import Static


class DocumentResource(resources.ModelResource):
    """
    Resource to export Documents from the discipline view.
    """

    # pylint: disable=pointless-statement
    ExportActionMixin.export_admin_action

    # pylint: disable=super-init-not-called
    def __init__(self, for_profession=None):
        self.for_profession = for_profession
        self.relevant_training_sets = (
            for_profession.get_nested_training_sets() if for_profession else None
        )

    word = fields.Field(column_name=_("Word"), attribute="word")

    word_type = fields.Field(column_name=_("Word type"), attribute="word_type")

    singular_article = fields.Field(
        column_name=_("Singular Article"),
        attribute="singular_article",
    )

    def dehydrate_singular_article(self, document):
        """
        Method to show the actual singular article and not their integer.
        """
        for x in Static.singular_article_choices:
            if x[0] == document.singular_article:
                return x[1]
        return "-"

    plural_article = fields.Field(
        column_name=_("Plural Article"),
        attribute="plural_article_choices",
    )

    def dehydrate_plural_article(self, document):
        """
        Method to show the actual plural article and not their integer.
        """
        for x in Static.plural_article_choices:
            if x[0] == document.plural_article:
                return x[1]
        return "-"

    has_audio = fields.Field(column_name=_("Has audio?"), attribute="word")

    def dehydrate_has_audio(self, document):
        """
        Returns yes if audio exists and no if it doesn't.
        """
        if bool(document.audio) is True:
            return _("Yes")
        return _("No")

    example_sentence = fields.Field(
        column_name=_("Example sentence"), attribute="example_sentence"
    )

    creation_date = fields.Field(
        column_name=_("Creation date"), attribute="creation_date"
    )

    def dehydrate_creation_date(self, document):
        """
        Only show first 16 characters of date (date, and hours & minutes).
        """
        return str(document.creation_date)[:16]

    training_sets = fields.Field(
        column_name=_("Training Sets"), attribute="training_sets"
    )

    def dehydrate_training_sets(self, document):
        """
        Method to get relevant training sets.
        """
        relevant_training_sets = (
            self.relevant_training_sets
            if self.relevant_training_sets
            else document.training_sets.values_list("id", flat=True)
        )
        return " | ".join(
            [
                t.title
                for t in document.training_sets.filter(id__in=relevant_training_sets)
            ]
        )

    class Meta:
        """
        Meta class of Document resource
        """

        model = Document
        fields = (
            "word",
            "word_type",
            "singular_article",
            "plural_article",
            "has_audio",
            "example_sentence",
            "creation_date",
            "training_sets",
        )
