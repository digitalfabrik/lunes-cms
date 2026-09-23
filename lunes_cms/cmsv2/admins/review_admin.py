from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.models import Review
from lunes_cms.cmsv2.models.static import (
    get_color_by_review_status,
    get_initials_of_user,
)


class ReviewAdmin(BaseAdmin):
    """
    Admin interface for the Review model.

    This admin class provides a comprehensive interface for having an overview of open reviews,
    including their status, assignment and feedback.
    """

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "word_and_article",
                    "word_type",
                    "unit",
                    "review_status",
                    "jobs",
                    "image",
                    "audio",
                ],
            },
        ),
        (
            _("Meta information"),
            {
                "fields": [
                    "assigned_by",
                    "assigned_at",
                    "reviewer",
                    "creator",
                ],
            },
        ),
    ]
    list_filter = ["review_status", "reviewer"]
    search_fields = ["unit_word__word__word"]
    readonly_fields = [
        "word_and_article",
        "word_type",
        "unit",
        "jobs",
        "image",
        "audio",
        "creator",
        "reviewer",
        "assigned_by",
        "assigned_at",
        "completed_at",
    ]
    list_display = [
        "word_and_article",
        "word_type",
        "unit",
        "styled_review_status",
        "styled_reviewer",
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

    styled_review_status.short_description = _("Status")  # type: ignore[attr-defined]

    def styled_reviewer(self, obj: Review) -> SafeString:
        """returns the styled reviewer"""
        reviewer = obj.reviewer
        initials = get_initials_of_user(reviewer)
        return format_html(
            "<span class='badge py-2 mr-2 rounded-pill text-bg-primary'>{}</span> {}",
            initials,
            obj.reviewer,
        )

    styled_reviewer.short_description = _("Reviewer")  # type: ignore[attr-defined]
