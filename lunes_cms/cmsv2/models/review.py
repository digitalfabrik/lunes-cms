from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.db.models.fields.files import FieldFile, ImageFieldFile
from django.utils.translation import gettext_lazy as _

from ..utils import create_resource_path
from .job import Job
from .static import (
    ProgressStatus,
    ReviewStatus,
    SingularArticle,
    WordType,
)

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from .unit import Unit
    from .word import Word


def upload_review_suggestions(_: models.Model, filename: str) -> str:
    """
    Upload path for reviewer-suggested images.
    """
    return create_resource_path("review_suggestions", filename)


class Review(models.Model):
    """
    Model for a single review
    """

    word = models.ForeignKey(
        "Word",
        on_delete=models.CASCADE,
        related_name="review_assignments",
        verbose_name=_("unit"),
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
    reasons = models.CharField(max_length=20, default="", verbose_name="reasons")
    comment = models.CharField(max_length=120, default="", verbose_name="comment")
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
    def word_article(self) -> int:
        """Returns the article of the word being reviewed."""
        return self.word.singular_article

    @property
    def word_type(self) -> str:
        """Returns the word_type of the word being reviewed."""
        return self.word.word_type

    @property
    def units(self) -> "QuerySet[Unit]":
        """Returns the units the word being reviewed belongs to."""
        return self.word.units.all()

    @property
    def jobs(self) -> "QuerySet[Job]":
        """Returns the jobs of the units the word being reviewed belongs to."""
        return Job.objects.filter(units__in=self.units).distinct()

    @property
    def image(self) -> ImageFieldFile:
        """Returns the image of the word being reviewed"""
        return self.word.image

    @property
    def audio(self) -> FieldFile:
        """Returns the audio of the word being reviewed"""
        return self.word.audio

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
                fields=["word", "reviewer"], name="unique_review_assignment"
            )
        ]
        verbose_name = _("Review")
        verbose_name_plural = _("Review")

    def __str__(self) -> str:
        return f"{self.word} – {self.reviewer}"
