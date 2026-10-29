from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from ..models import Notification


class ReadStatusListFilter(admin.SimpleListFilter):
    """
    Filter notifications by whether they were marked as read.
    """

    title = _("read status")
    parameter_name = "read"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> list[tuple[str, str]]:
        return [("no", str(_("Unread"))), ("yes", str(_("Read")))]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Notification]
    ) -> QuerySet[Notification]:
        if self.value() == "no":
            return queryset.filter(read_at=None)
        if self.value() == "yes":
            return queryset.exclude(read_at=None)
        return queryset


class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for the internal notifications (#1038).

    Every user only sees the notifications addressed to them, superusers
    included.
    """

    list_display = [
        "message",
        "notification_type",
        "reviews_link",
        "created_at",
        "is_read",
    ]
    list_filter = [ReadStatusListFilter, "notification_type"]
    fields = ["message", "notification_type", "reviews_link", "created_at", "read_at"]
    readonly_fields = [
        "message",
        "notification_type",
        "reviews_link",
        "created_at",
        "read_at",
    ]
    actions = ["mark_as_read", "mark_as_unread"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Notification]:
        return (
            super()
            .get_queryset(request)
            .filter(recipient_id=request.user.pk)
            .select_related("expert", "unit")
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active

    def has_view_permission(
        self, request: HttpRequest, obj: Notification | None = None
    ) -> bool:
        return request.user.is_active

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Notification | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: Notification | None = None
    ) -> bool:
        return request.user.is_active

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """
        Mark a notification as read once its recipient opens it.
        """
        self.get_queryset(request).filter(pk=object_id, read_at=None).update(
            read_at=timezone.now()
        )
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.display(description=_("read"), boolean=True)
    def is_read(self, obj: Notification) -> bool:
        """Whether the notification was marked as read"""
        return obj.is_read

    @admin.display(description=_("reviews"))
    def reviews_link(self, obj: Notification) -> SafeString:
        """A link to the reviews of the expert the notification is about"""
        url = reverse("admin:cmsv2_review_changelist")
        return format_html(
            '<a href="{}?reviewer__id__exact={}">{}</a>',
            url,
            obj.expert_id,
            _("Show reviews of %(expert)s") % {"expert": obj.expert},
        )

    @admin.action(description=_("Mark as read"))
    def mark_as_read(
        self, request: HttpRequest, queryset: QuerySet[Notification]
    ) -> None:
        """
        Mark the selected notifications as read
        """
        count = queryset.filter(read_at=None).update(read_at=timezone.now())
        self.message_user(
            request,
            _("Marked %(count)d notification(s) as read.") % {"count": count},
            messages.SUCCESS,
        )

    @admin.action(description=_("Mark as unread"))
    def mark_as_unread(
        self, request: HttpRequest, queryset: QuerySet[Notification]
    ) -> None:
        """
        Mark the selected notifications as unread
        """
        count = queryset.exclude(read_at=None).update(read_at=None)
        self.message_user(
            request,
            _("Marked %(count)d notification(s) as unread.") % {"count": count},
            messages.SUCCESS,
        )
