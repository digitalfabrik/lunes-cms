from django.db import models


class AnalyticsEvent(models.Model):
    """
    Analytics event
    """

    class ExerciseType(models.TextChoices):
        """
        Exercise types matching the app's ExerciseKeys.
        """

        WORD_LIST = "word_list", "Word List"
        WORD_CHOICE = "word_choice", "Word Choice"

    class EventType(models.TextChoices):
        """
        Supported analytics event types
        """

        JOB_SELECTED = "job_selected"
        SESSION_START = "session_start"
        SESSION_END = "session_end"
        MODULE_DURATION = "module_duration"
        EXERCISE_DROPOUT = "exercise_dropout"
        EXERCISE_REPETITION = "exercise_repetition"

    installation_id = models.CharField(
        max_length=255,
        db_index=True,
    )
    event_type = models.CharField(
        max_length=100,
        choices=EventType.choices,
        db_index=True,
    )
    timestamp = models.DateTimeField()
    payload = models.JSONField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        """
        Meta class
        """

        indexes = [
            models.Index(fields=["timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return (
            f"{self.installation_id} | {self.event_type} | {self.timestamp.isoformat()}"
        )
