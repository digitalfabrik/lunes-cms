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
    unit_id = models.IntegerField(null=True)
    job_id = models.IntegerField(null=True)

    # aggregated fields
    total_sessions = models.IntegerField(default=0)
    total_duration_seconds = models.IntegerField(default=0)

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["date", "exercise_type", "unit_id", "job_id"],
                name="unique_module_duration_key",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(unit_id__isnull=True, job_id__isnull=False)
                    | models.Q(unit_id__isnull=False, job_id__isnull=True)
                ),
                name="module_duration_exclusive_unit_or_job_id",
            ),
        ]

    def __str__(self) -> str:
        key = (
            f"unit={self.unit_id}" if self.unit_id is not None else f"job={self.job_id}"
        )
        return (
            f"Module duration aggregate ({self.date}, {self.exercise_type}, "
            f"{key}): {self.total_sessions} | {self.total_duration_seconds}"
        )
