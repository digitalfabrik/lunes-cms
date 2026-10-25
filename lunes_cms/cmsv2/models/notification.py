from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .static import NotificationType


class Notification(models.Model):
    """
    An internal notification about the review work of an expert, see #1038.

    Every notification belongs to a single user: a notification sent to three
    users is stored as three notifications, each of which is marked as read on
    its own.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient"),
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        verbose_name=_("notification type"),
    )
    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_about",
        verbose_name=_("expert"),
        help_text=_("The expert whose review work the notification is about"),
    )
    unit = models.ForeignKey(
        "Unit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
        verbose_name=_("unit"),
    )
    count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("count"),
        help_text=_("The number of flagged or overdue reviews"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("read at"))

    @property
    def is_read(self) -> bool:
        """Whether the recipient has marked the notification as read"""
        return self.read_at is not None

    @property
    def message(self) -> str:
        """The text of the notification in the active language"""
        expert = self.expert.get_full_name() or self.expert.username
        unit = str(self.unit) if self.unit else _("a deleted unit")
        if self.notification_type == NotificationType.REVIEW_COMPLETED:
            return _("%(expert)s has finished the review of %(unit)s.") % {
                "expert": expert,
                "unit": unit,
            }
        if self.notification_type == NotificationType.MANY_REJECTIONS:
            return _("%(expert)s has flagged %(count)d words of %(unit)s as wrong.") % {
                "expert": expert,
                "count": self.count,
                "unit": unit,
            }
        return _(
            "%(expert)s has %(count)d reviews which are pending for more than %(days)d days."
        ) % {
            "expert": expert,
            "count": self.count,
            "days": settings.REVIEW_SLOW_EXPERT_DAYS,
        }

    def __str__(self) -> str:
        return self.message

    class Meta:
        """
        Meta class for the Notification model.
        """

        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
