from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import create_resource_path
from .static import REVIEW_STATUS_CHOICES


def upload_review_suggestions(instance, filename):
    """
    Upload path for reviewer-suggested images.
    """
    return create_resource_path("review_suggestions", filename)


class ReviewAssignment(models.Model):
    """
    Assigns a reviewer to review content for a specific unit.
    A single assignment covers all words within that unit.
    """

    unit = models.ForeignKey(
        "Unit",
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
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("assigned at"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("completed at")
    )

    class Meta:
        """
        Meta class for ReviewAssignment model.
        """

        unique_together = ("unit", "reviewer")
        verbose_name = _("Review Assignment")
        verbose_name_plural = _("Review Assignments")

    def __str__(self):
        return f"{self.unit} – {self.reviewer}"


class ImageReview(models.Model):
    """
    Tracks individual image review decisions.
    Can be for either a word-level image or a unit-specific image (UnitWordRelation).
    """

    unit_word_relation = models.ForeignKey(
        "UnitWordRelation",
        on_delete=models.CASCADE,
        related_name="image_reviews",
        verbose_name=_("unit-word relation"),
    )
    is_unit_specific_image = models.BooleanField(
        default=False,
        verbose_name=_("unit-specific image"),
        help_text=_(
            "True if reviewing UnitWordRelation.image, False if reviewing Word.image"
        ),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="image_reviews",
        verbose_name=_("reviewer"),
    )
    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default=REVIEW_STATUS_CHOICES[0][0],
        verbose_name=_("status"),
    )
    comment = models.TextField(blank=True, verbose_name=_("comment"))
    suggested_image = models.ImageField(
        upload_to=upload_review_suggestions,
        blank=True,
        null=True,
        verbose_name=_("suggested image"),
        help_text=_("Alternative image suggested by reviewer"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        """
        Meta class for ImageReview model.
        """

        unique_together = ("unit_word_relation", "reviewer")
        verbose_name = _("Image Review")
        verbose_name_plural = _("Image Reviews")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.unit_word_relation} – {self.reviewer} ({self.status})"

    @property
    def word(self):
        """Returns the word being reviewed."""
        return self.unit_word_relation.word

    @property
    def unit(self):
        """Returns the unit context of the review."""
        return self.unit_word_relation.unit

    @property
    def reviewed_image(self):
        """Returns the actual image being reviewed."""
        if self.is_unit_specific_image:
            return self.unit_word_relation.image
        return self.unit_word_relation.word.image
