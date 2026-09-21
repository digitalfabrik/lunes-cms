from __future__ import annotations

from typing import Any, Callable, cast, ClassVar

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..areas import area_of_unit, area_of_word
from ..feedback_filter import filter_feedback_by_creator_and_area
from ..models import Area, Feedback, Job, Unit, Word
from .feedback_area_filter import FeedbackAreaListFilter


class FeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for feedback.
    Inheriting from `admin.ModelAdmin`.
    """

    model = Feedback
    list_display: list[str | Callable[[Any], str | bool]] = [
        "comment",
        "content_object_link",
        "content_type",
        "area",
        "created_date",
        "read_by",
    ]
    readonly_fields: ClassVar[list[str]] = [
        "comment",
        "content_object_link",
        "content_type",
        "created_date",
        "read_by",
    ]
    search_fields = ["comment"]
    list_filter = ["content_type", FeedbackAreaListFilter, "read_by"]
    sortable_by = ["content_type", "created_date", "read_by"]
    actions = ["mark_as_read", "mark_as_unread"]

    def area(self, obj: Feedback) -> str:
        """
        The area of the job, unit or word the feedback refers to, for display
        in the list view. Empty for content of the main app.
        """
        model_name = obj.content_type.model
        area: Area | None
        if model_name == "job":
            area = cast(Job, obj.content_object).area
        elif model_name == "unit":
            area = area_of_unit(cast(Unit, obj.content_object))
        else:
            area = area_of_word(cast(Word, obj.content_object))
        return str(area) if area else ""

    area.short_description = _("area")  # type: ignore[attr-defined]

    def has_add_permission(
        self, request: HttpRequest, _obj: Feedback | None = None
    ) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, _obj: Feedback | None = None
    ) -> bool:
        return False

    @admin.action(description=_("Mark as read"))
    def mark_as_read(self, request: HttpRequest, queryset: QuerySet[Feedback]) -> None:
        """
        Action to mark selected items as read by user

        :param request: The current request
        :type request: ~django.http.HttpRequest

        :param queryset: The queryset of selected feedback entries
        :type queryset: ~django.db.models.query.QuerySet
        """
        queryset.update(read_by=request.user)
        messages.success(
            request,
            _(
                "The selected feedback entries were successfully marked as read.",
            ),
        )

    @admin.action(description=_("Mark as unread"))
    def mark_as_unread(
        self, request: HttpRequest, queryset: QuerySet[Feedback]
    ) -> None:
        """
        Action to mark selected items as unread

        :param request: The current request
        :type request: ~django.http.HttpRequest

        :param queryset: The queryset of selected feedback entries
        :type queryset: ~django.db.models.query.QuerySet
        """
        queryset.update(read_by=None)
        messages.success(
            request,
            _(
                "The selected feedback entries were successfully marked as unread.",
            ),
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Feedback]:
        feedback_entries = super().get_queryset(request)

        if not request.user.is_superuser:
            return filter_feedback_by_creator_and_area(feedback_entries, request.user)  # type: ignore[arg-type]

        return feedback_entries

    class Media:
        """
        Media class for Feedback Admin
        """

        css = {"all": ("css/feedback.css",)}
        js = ("js/color_unread_feedback.js",)
