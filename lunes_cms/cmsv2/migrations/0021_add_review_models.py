import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import lunes_cms.cmsv2.models.review


class Migration(migrations.Migration):
    """
    Migration to add ImageReview and ReviewAssignment models for content review workflow.
    """

    dependencies = [
        ("cmsv2", "0020_unitwordrelation_example_sentence_audio_regenerated"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageReview",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_unit_specific_image",
                    models.BooleanField(
                        default=False,
                        help_text="True if reviewing UnitWordRelation.image, False if reviewing Word.image",
                        verbose_name="unit-specific image",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending Review"),
                            ("APPROVED", "Approved"),
                        ],
                        default="PENDING",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                ("comment", models.TextField(blank=True, verbose_name="comment")),
                (
                    "suggested_image",
                    models.ImageField(
                        blank=True,
                        help_text="Alternative image suggested by reviewer",
                        null=True,
                        upload_to=lunes_cms.cmsv2.models.review.upload_review_suggestions,
                        verbose_name="suggested image",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="updated at"),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="image_reviews",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reviewer",
                    ),
                ),
                (
                    "unit_word_relation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="image_reviews",
                        to="cmsv2.unitwordrelation",
                        verbose_name="unit-word relation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Image Review",
                "verbose_name_plural": "Image Reviews",
                "ordering": ["-created_at"],
                "unique_together": {("unit_word_relation", "reviewer")},
            },
        ),
        migrations.CreateModel(
            name="ReviewAssignment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "assigned_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="assigned at"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="completed at"
                    ),
                ),
                (
                    "assigned_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_review_assignments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="assigned by",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_assignments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="reviewer",
                    ),
                ),
                (
                    "unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_assignments",
                        to="cmsv2.unit",
                        verbose_name="unit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Review Assignment",
                "verbose_name_plural": "Review Assignments",
                "unique_together": {("unit", "reviewer")},
            },
        ),
    ]
