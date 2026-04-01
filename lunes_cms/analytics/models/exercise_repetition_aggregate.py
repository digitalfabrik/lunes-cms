from django.db import models

from lunes_cms.analytics.models.analytics_event import AnalyticsEvent


class ExerciseRepetitionAggregate(models.Model):
    """
    Aggregate of exercise_repetition analytics events.
    Tracks how many times the same exercise/unit combo is started within a session.
    """

    unit_id = models.IntegerField()
    exercise_type = models.CharField(
        max_length=50,
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    repetition_count = models.IntegerField()
    start_count = models.IntegerField()
    date = models.DateField(db_index=True)

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["unit_id", "exercise_type", "date"],
                name="unique_exercise_repetition_per_session",
            ),
        ]

    def __str__(self) -> str:
        return f"Unit {self.unit_id} | Exercise {self.exercise_type} | Repetition {self.repetition_count} | Date {self.date} | Start Count {self.start_count}"
