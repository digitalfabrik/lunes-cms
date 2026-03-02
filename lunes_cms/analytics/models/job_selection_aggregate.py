from django.db import models
from lunes_cms.cmsv2.models import Job


class JobSelectionAggregate(models.Model):
    """
    Aggregate class for JobSelection
    """

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="selection_aggregates"
    )
    selection_count = models.IntegerField()
    date = models.DateField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["job", "date"]),
        ]

    def __str__(self):
        return f"{self.job} – {self.date}: {self.selection_count}"
