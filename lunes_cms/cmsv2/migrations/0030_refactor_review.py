import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration file for the review model"""

    dependencies = [
        ("cmsv2", "0029_backfill_null_check_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Review",
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
                    "reasons",
                    models.CharField(default="", max_length=20, verbose_name="reasons"),
                ),
                (
                    "comment",
                    models.CharField(
                        default="", max_length=120, verbose_name="comment"
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
                    "review_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending Review"),
                            ("CHANGE_REQUESTED", "Change requested"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("CANNOT_BE_ASSESSED", "Cannot be assessed"),
                        ],
                        default="PENDING",
                        max_length=20,
                        verbose_name="review status",
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
                    "word",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_assignments",
                        to="cmsv2.word",
                        verbose_name="unit",
                    ),
                ),
            ],
            options={
                "verbose_name": "Review",
                "verbose_name_plural": "Review",
            },
        ),
        migrations.DeleteModel(
            name="ImageReview",
        ),
        migrations.DeleteModel(
            name="ReviewAssignment",
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(
                fields=("word", "reviewer"), name="unique_review_assignment"
            ),
        ),
    ]
