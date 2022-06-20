from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

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

    class Media:
        css = {"all": ("css/feedback.css",)}
