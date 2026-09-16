from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.models import Review
from lunes_cms.cmsv2.models.static import get_color_by_review_status


class ReviewAdmin(BaseAdmin):
    """
    Admin interface for the Review model.

    This admin class provides a comprehensive interface for having an overview of open reviews,
    including their status, assignment and feedback.
    """

    fields = [
        "word_and_article",
        "word_type",
        "unit",
        "review_status",
        "reviewer",
    ]
    list_filter = ["review_status", "reviewer"]
    search_fields = ["unit_word__word__word"]
    readonly_fields = [
        "word_and_article",
        "word_type",
        "unit",
    ]
    list_display = [
        "word_and_article",
        "word_type",
        "unit",
        "styled_review_status",
        "reviewer",
    ]

    def word_and_article(self, obj: Review) -> SafeString:
        """Returns the word with article, separated by a line break."""
        word = obj.unit_word.word
        return format_html("<b>{}</b><br>{}", word.word, word.singular_article_as_text)

    word_and_article.short_description = _("word and article")  # type: ignore[attr-defined]

    def styled_review_status(self, obj: Review) -> SafeString:
        """Returns the styled review status"""
        color = get_color_by_review_status(obj.review_status)
        return format_html(
            "<span class='badge rounded-pill {}'>{}</span>",
            color,
            obj.get_review_status_display(),
        )
