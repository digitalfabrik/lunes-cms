from django.db import models


class JobSelectionAggregate(models.Model):
    """
    Aggregate of job_selected analytics events
    """

    # Not a foreign field so that the aggregated statistics stay valid after jobs are deleted
    job_id = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)

    # aggregated fields
    selection_count = models.IntegerField()

    class Meta:
        """
        Meta class
        """

        constraints = [
            models.UniqueConstraint(
                fields=["job_id", "date"],
                name="unique_job_selection_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"Job aggregate {self.job_id} | {self.date} | {self.selection_count}"
