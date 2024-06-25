from django.contrib import admin, messages

from django.utils.translation import gettext_lazy as _

from ..feedback_filter import filter_feedback_by_creator
from ..models import Feedback


class FeedbackAdmin(admin.ModelAdmin):
    """
    Admin interface for feedback.
    Inheriting from `admin.ModelAdmin`.
    """

    model = Feedback
    list_display = readonly_fields = [
        "comment",
        "content_object_link",
        "content_type",
        "created_date",
        "read_by",
    ]
    search_fields = ["comment"]
    list_filter = ["content_type", "read_by"]
    sortable_by = ["content_type", "created_date", "read_by"]
    actions = ["mark_as_read", "mark_as_unread"]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.action(description=_("Mark as read"))
    def mark_as_read(self, request, queryset):
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
    def mark_as_unread(self, request, queryset):
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

    def get_queryset(self, request):
        feedback_entries = super().get_queryset(request)

        if not request.user.is_superuser:
            return filter_feedback_by_creator(feedback_entries, request.user)

        return feedback_entries

    class Media:
        """
        Media class for Feedback Admin
        """

        css = {"all": ("css/feedback.css",)}
        js = ("js/color_unread_feedback.js",)
