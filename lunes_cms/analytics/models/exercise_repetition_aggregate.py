from django.db import models

from lunes_cms.analytics.models.analytics_event import AnalyticsEvent


class ExerciseRepetitionAggregate(models.Model):
    """
    Aggregate of exercise_repetition analytics events.
    Tracks how many times the same exercise/unit combo is started within a session.
    """

    unit_id = models.IntegerField(null=True)
    job_id = models.IntegerField(null=True)
    exercise_type = models.CharField(
        max_length=50,
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    session_id = models.CharField(max_length=32)
    repetition_count = models.PositiveIntegerField()

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["unit_id", "job_id", "exercise_type", "session_id"],
                name="unique_exercise_repetition_per_session",
                nulls_distinct=False,
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Unit {self.unit_id} | Job {self.job_id} | Exercise {self.exercise_type} | "
            f"Session ID {self.session_id} | Repetitions {self.repetition_count}"
        )
