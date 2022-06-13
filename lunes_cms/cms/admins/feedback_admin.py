from django.contrib import admin
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

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    class Media:
        css = {"all": ("css/feedback.css",)}
