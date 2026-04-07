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
                    "dropout_position",
                    "total_items",
                ],
                name="unique_dropout_key",
                nulls_distinct=False,
            )
        ]

    def __str__(self) -> str:
        return (
            f"Dropout aggregate ({self.date}, type={self.exercise_type}, "
            f"unit={self.unit_id}, pos={self.dropout_position}/{self.total_items}): "
            f"{self.dropout_count}"
        )
