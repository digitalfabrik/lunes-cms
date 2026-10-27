from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    """
    The kinds of new content an expert is told about
    """

    UNIT_ASSIGNED = "unit_assigned", _("Unit assigned")
    WORD_ADDED = "word_added", _("Word added")
    IMAGE_ADDED = "image_added", _("Image added")


class PendingNotification(models.Model):
    """
    New content for an expert to review that is not announced yet. The
    ``send_expert_digest`` command sends every expert one email with all of
    their pending notifications and deletes them afterwards.
    """

    expert = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_notifications",
        verbose_name=_("expert"),
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        verbose_name=_("notification type"),
    )
    unit = models.ForeignKey(
        "Unit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pending_notifications",
        verbose_name=_("unit"),
        help_text=_("The assigned unit"),
    )
    unit_word = models.ForeignKey(
        "UnitWordRelation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="pending_notifications",
        verbose_name=_("word"),
        help_text=_("The added word or the word with the new image"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    def __str__(self) -> str:
        return f"{self.get_notification_type_display()}: {self.unit or self.unit_word}"

    class Meta:
        """
        Meta class for PendingNotification model.
        """

        verbose_name = _("pending notification")
        verbose_name_plural = _("pending notifications")
