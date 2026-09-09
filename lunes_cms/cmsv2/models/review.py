from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import create_resource_path
from .static import (
    ProgressStatus,
    ReviewStatus,
)


def upload_review_suggestions(_: models.Model, filename: str) -> str:
    """
    Upload path for reviewer-suggested images.
    """
    return create_resource_path("review_suggestions", filename)


class Review(models.Model):
    """
    Model for a single review
    """

    unit_word = models.ForeignKey(
        "UnitWordRelation",
        on_delete=models.CASCADE,
        related_name="review_assignments",
        verbose_name=_("word"),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_assignments",
        verbose_name=_("reviewer"),
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_review_assignments",
        verbose_name=_("assigned by"),
    )
    reason = models.CharField(max_length=20, default="", verbose_name=_("reason"))
    comment = models.CharField(max_length=120, default="", verbose_name=_("comment"))
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("assigned at"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("completed at")
    )
    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        verbose_name=_("review status"),
    )

    @property
    def progress_status(self) -> ProgressStatus:
        """Returns the status of a review"""
        return (
            ProgressStatus.IN_REVIEW
            if not self.completed_at
            else ProgressStatus.COMPLETED
        )

    class Meta:
        """
        Meta class for Review model.
        """

        constraints = [
            models.UniqueConstraint(
                fields=["unit_word", "reviewer"], name="unique_review_assignment"
            )
        ]
        verbose_name = _("Review")
        verbose_name_plural = _("Review")

    def __str__(self) -> str:
        return f"{self.unit_word} – {self.reviewer}"
