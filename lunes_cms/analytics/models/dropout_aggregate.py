from django.db import models

from .analytics_event import AnalyticsEvent


class DropoutAggregate(models.Model):
    """
    Aggregate of exercise dropout events.
    Tracks where users leave exercises before completion.
    """

    date = models.DateField(db_index=True)
    exercise_type = models.CharField(
        max_length=50,
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    unit_id = models.IntegerField(null=True)
    job_id = models.IntegerField(null=True)
    vocabulary_item_id = models.IntegerField(null=True)
    dropout_position = models.IntegerField()
    total_items = models.IntegerField()

    # aggregated fields
    dropout_count = models.IntegerField(default=0)

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "date",
                    "exercise_type",
                    "unit_id",
                    "job_id",
                    "vocabulary_item_id",
                    "dropout_position",
                    "total_items",
                ],
                name="unique_dropout_key",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(unit_id__isnull=True, job_id__isnull=False)
                    | models.Q(unit_id__isnull=False, job_id__isnull=True)
                ),
                name="dropout_exclusive_unit_or_job_id",
            ),
        ]

    def __str__(self) -> str:
        key = (
            f"unit={self.unit_id}" if self.unit_id is not None else f"job={self.job_id}"
        )
        return (
            f"Dropout aggregate ({self.date}, type={self.exercise_type}, "
            f"{key}, vocab={self.vocabulary_item_id}, "
            f"pos={self.dropout_position}/{self.total_items}): {self.dropout_count}"
        )
