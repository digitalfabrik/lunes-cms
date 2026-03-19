from django.db import models


class SessionAggregate(models.Model):
    """
    Aggregate of session start and end events
    """

    date = models.DateField(db_index=True, unique=True)

    # aggregated fields
    total_sessions = models.IntegerField(default=0)
    total_duration_seconds = models.IntegerField(default=0)
    duration_buckets = models.JSONField(default=dict)

    class Meta:
        """
        Meta class
        """

    def __str__(self) -> str:
        return f"Session aggregate ({self.date}): {self.total_sessions} | {self.total_duration_seconds} | {self.duration_buckets}"
