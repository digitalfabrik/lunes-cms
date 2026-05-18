from django.db import models

from lunes_cms.analytics.models.analytics_event import AnalyticsEvent


class ModuleDurationAggregate(models.Model):
    """
    Aggregate of module duration events
    """

    date = models.DateField(db_index=True)
    exercise_type = models.CharField(
        max_length=50,
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    unit_id = models.IntegerField()

    # aggregated fields
    total_sessions = models.IntegerField(default=0)
    total_duration_seconds = models.IntegerField(default=0)

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["date", "exercise_type", "unit_id"],
                name="unique_module_duration_key",
            )
        ]

    def __str__(self) -> str:
        return f"Module duration aggregate ({self.date}, {self.exercise_type}, {self.unit_id}): {self.total_sessions} | {self.total_duration_seconds}"
