from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TestCase

from lunes_cms.analytics.models import AnalyticsEvent, JobSelectionAggregate
from lunes_cms.cmsv2.models.job import Job


class AggregateAnalyticsCommandTests(TestCase):
    """
    Tests for the aggregate_analytics management command.
    """

    def setUp(self) -> None:
        self.job1 = Job.objects.create(name="Job 1")
        self.job2 = Job.objects.create(name="Job 2")

    def _create_event(self, job_id: int, action: str, timestamp: str) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="job_selected",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={"job_id": job_id, "action": action},
        )

    def test_aggregates_single_day(self) -> None:
        """Test basic aggregation of events into a single day"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(self.job1.id, "add", "2026-01-15T11:00:00")
        self._create_event(self.job1.id, "remove", "2026-01-15T12:00:00")

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        agg = JobSelectionAggregate.objects.get(job_id=self.job1.id)
        self.assertEqual(agg.selection_count, 1)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate aggregates"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(self.job1.id, "add", "2026-01-16T10:00:00")

        call_command("aggregate_analytics")

        self.assertEqual(JobSelectionAggregate.objects.count(), 2)

    def test_aggregates_multiple_jobs(self) -> None:
        """Test that events for different jobs create separate aggregates"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(self.job2.id, "add", "2026-01-15T10:00:00")

        call_command("aggregate_analytics")

        self.assertEqual(JobSelectionAggregate.objects.count(), 2)
        self.assertEqual(
            JobSelectionAggregate.objects.get(job_id=self.job1.id).selection_count, 1
        )
        self.assertEqual(
            JobSelectionAggregate.objects.get(job_id=self.job2.id).selection_count, 1
        )

    def test_increments_existing_aggregate(self) -> None:
        """Test that running twice increments existing aggregates"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        call_command("aggregate_analytics")

        self._create_event(self.job1.id, "add", "2026-01-15T14:00:00")
        call_command("aggregate_analytics")

        agg = JobSelectionAggregate.objects.get(job_id=self.job1.id)
        self.assertEqual(agg.selection_count, 2)

    def test_no_events(self) -> None:
        """Test that running with no events does nothing"""
        call_command("aggregate_analytics")
        self.assertEqual(JobSelectionAggregate.objects.count(), 0)

    def test_nonexistent_job_id(self) -> None:
        """Test that events with nonexistent job_ids are aggregated normally"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(99999, "add", "2026-01-15T10:00:00")

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        self.assertEqual(JobSelectionAggregate.objects.count(), 2)
        self.assertEqual(
            JobSelectionAggregate.objects.get(job_id=99999).selection_count, 1
        )

    def test_only_removes_count(self) -> None:
        """Test aggregation with only remove actions gives negative count"""
        self._create_event(self.job1.id, "remove", "2026-01-15T10:00:00")
        self._create_event(self.job1.id, "remove", "2026-01-15T11:00:00")

        call_command("aggregate_analytics")

        agg = JobSelectionAggregate.objects.get(job_id=self.job1.id)
        self.assertEqual(agg.selection_count, -2)
