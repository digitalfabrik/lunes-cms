from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TestCase

from lunes_cms.analytics.models import (
    AnalyticsEvent,
    DropoutAggregate,
    JobSelectionAggregate,
    ModuleDurationAggregate,
    SessionAggregate,
)
from lunes_cms.cmsv2.models.job import Job


class JobSelectionAggregateTests(TestCase):
    """
    Tests for job selection event aggregation.
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


class SessionAggregateTests(TestCase):
    """
    Tests for session event aggregation.
    """

    def _create_session_event(
        self, session_id: str, event_type: str, timestamp: str
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type=event_type,
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={"session_id": session_id},
        )

    def _create_session(
        self, session_id: str, start: str, end: str
    ) -> tuple[AnalyticsEvent, AnalyticsEvent]:
        return (
            self._create_session_event(session_id, "session_start", start),
            self._create_session_event(session_id, "session_end", end),
        )

    def test_valid_session_creates_aggregate(self) -> None:
        """A single valid session pair creates a SessionAggregate"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 1)
        self.assertEqual(agg.total_duration_seconds, 30)
        self.assertEqual(agg.duration_buckets, {"0-1": 1})

    def test_multiple_sessions_same_day(self) -> None:
        """Multiple valid sessions on the same day are aggregated together"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:10:00")

        call_command("aggregate_analytics")

        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 2)
        self.assertEqual(agg.total_duration_seconds, 630)
        self.assertEqual(agg.duration_buckets, {"0-1": 1, "5-15": 1})

    def test_sessions_on_different_days(self) -> None:
        """Sessions on different days create separate aggregates"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:02:00")
        self._create_session("s2", "2026-01-16T10:00:00", "2026-01-16T10:02:00")

        call_command("aggregate_analytics")

        self.assertEqual(SessionAggregate.objects.count(), 2)

    def test_increments_existing_aggregate(self) -> None:
        """Running the command twice increments existing aggregates"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        call_command("aggregate_analytics")

        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:00:30")
        call_command("aggregate_analytics")

        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 2)
        self.assertEqual(agg.total_duration_seconds, 60)
        self.assertEqual(agg.duration_buckets, {"0-1": 2})

    def test_increments_different_buckets(self) -> None:
        """Running the command twice with different buckets updates both"""
        # 30 seconds -> bucket "0-1"
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        call_command("aggregate_analytics")

        # 10 minutes -> bucket "5-15"
        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:10:00")
        call_command("aggregate_analytics")

        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 2)
        self.assertEqual(agg.duration_buckets, {"0-1": 1, "5-15": 1})

    def test_ignores_start_without_end(self) -> None:
        """A session_start without a matching session_end is ignored"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")

        call_command("aggregate_analytics")

        self.assertEqual(SessionAggregate.objects.count(), 0)
        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_ignores_end_without_start(self) -> None:
        """A session_end without a matching session_start is ignored"""
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")

        call_command("aggregate_analytics")

        self.assertEqual(SessionAggregate.objects.count(), 0)
        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_ignores_duplicate_start_events(self) -> None:
        """A session_id with two start events and one end event is ignored"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")
        self._create_session_event("s1", "session_start", "2026-01-15T10:01:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")

        call_command("aggregate_analytics")

        self.assertEqual(SessionAggregate.objects.count(), 0)
        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_ignores_duplicate_end_events(self) -> None:
        """A session_id with one start event and two end events is ignored"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:06:00")

        call_command("aggregate_analytics")

        self.assertEqual(SessionAggregate.objects.count(), 0)
        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_invalid_sessions_dont_affect_valid_ones(self) -> None:
        """Invalid sessions are discarded but valid ones are still aggregated"""
        # Valid session
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:02:00")
        # Invalid: start without end
        self._create_session_event("s2", "session_start", "2026-01-15T11:00:00")
        # Invalid: duplicate starts
        self._create_session_event("s3", "session_start", "2026-01-15T12:00:00")
        self._create_session_event("s3", "session_start", "2026-01-15T12:01:00")
        self._create_session_event("s3", "session_end", "2026-01-15T12:05:00")

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 1)
        self.assertEqual(agg.total_duration_seconds, 120)

    def test_duration_bucket_boundaries(self) -> None:
        """Test that durations land in the correct buckets"""
        # Exactly 1 minute -> bucket "0-1"
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:01:00")
        # 1 minute 1 second -> bucket "1-5"
        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:01:01")
        # Exactly 5 minutes -> bucket "1-5"
        self._create_session("s3", "2026-01-15T12:00:00", "2026-01-15T12:05:00")
        # 5 minutes 1 second -> bucket "5-15"
        self._create_session("s4", "2026-01-15T13:00:00", "2026-01-15T13:05:01")
        # 30 minutes -> bucket "15-30"
        self._create_session("s5", "2026-01-15T14:00:00", "2026-01-15T14:30:00")
        # 31 minutes -> bucket "30-"
        self._create_session("s6", "2026-01-15T15:00:00", "2026-01-15T15:31:00")

        call_command("aggregate_analytics")

        agg = SessionAggregate.objects.get(date="2026-01-15")
        self.assertEqual(agg.total_sessions, 6)
        self.assertEqual(
            agg.duration_buckets,
            {"0-1": 1, "1-5": 2, "5-15": 1, "15-30": 1, "30-": 1},
        )


class ModuleDurationAggregateTests(TestCase):
    """
    Tests for module duration event aggregation.
    """

    def _create_event(
        self, exercise_type: int, unit_id: int, timestamp: str, duration_seconds: int
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="module_duration",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_type": exercise_type,
                "unit_id": unit_id,
                "duration_seconds": duration_seconds,
            },
        )

    def test_aggregates_single_day(self) -> None:
        """Test basic aggregation of module duration events into a single day"""
        self._create_event(1, 10, "2026-01-15T10:00:00", 60)
        self._create_event(1, 10, "2026-01-15T11:00:00", 90)

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        agg = ModuleDurationAggregate.objects.get(
            exercise_type=1, unit_id=10, date="2026-01-15"
        )
        self.assertEqual(agg.total_sessions, 2)
        self.assertEqual(agg.total_duration_seconds, 150)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate aggregates"""
        self._create_event(1, 10, "2026-01-15T10:00:00", 60)
        self._create_event(1, 10, "2026-01-16T10:00:00", 60)

        call_command("aggregate_analytics")

        self.assertEqual(ModuleDurationAggregate.objects.count(), 2)

    def test_aggregates_different_exercise_types(self) -> None:
        """Test that different exercise types create separate aggregates"""
        self._create_event(1, 10, "2026-01-15T10:00:00", 60)
        self._create_event(2, 10, "2026-01-15T10:00:00", 60)

        call_command("aggregate_analytics")

        self.assertEqual(ModuleDurationAggregate.objects.count(), 2)
        self.assertEqual(
            ModuleDurationAggregate.objects.get(
                exercise_type=1, unit_id=10
            ).total_sessions,
            1,
        )
        self.assertEqual(
            ModuleDurationAggregate.objects.get(
                exercise_type=2, unit_id=10
            ).total_sessions,
            1,
        )

    def test_aggregates_different_units(self) -> None:
        """Test that different unit IDs create separate aggregates"""
        self._create_event(1, 10, "2026-01-15T10:00:00", 60)
        self._create_event(1, 20, "2026-01-15T10:00:00", 90)

        call_command("aggregate_analytics")

        self.assertEqual(ModuleDurationAggregate.objects.count(), 2)
        self.assertEqual(
            ModuleDurationAggregate.objects.get(unit_id=10).total_duration_seconds, 60
        )
        self.assertEqual(
            ModuleDurationAggregate.objects.get(unit_id=20).total_duration_seconds, 90
        )

    def test_increments_existing_aggregate(self) -> None:
        """Test that running twice updates existing aggregates"""
        self._create_event(1, 10, "2026-01-15T10:00:00", 60)
        call_command("aggregate_analytics")

        self._create_event(1, 10, "2026-01-15T14:00:00", 40)
        call_command("aggregate_analytics")

        agg = ModuleDurationAggregate.objects.get(
            exercise_type=1, unit_id=10, date="2026-01-15"
        )
        self.assertEqual(agg.total_sessions, 2)
        self.assertEqual(agg.total_duration_seconds, 100)

    def test_no_events(self) -> None:
        """Test that running with no events does nothing"""
        call_command("aggregate_analytics")
        self.assertEqual(ModuleDurationAggregate.objects.count(), 0)


class DropoutAggregateTests(TestCase):
    """
    Tests for exercise dropout event aggregation.
    """

    def _create_event(  # pylint: disable=too-many-arguments
        self,
        *,
        exercise_type: str,
        unit_id: int | None,
        position: int,
        total: int,
        timestamp: str,
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_dropout",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_type": exercise_type,
                "unit_id": unit_id,
                "position": position,
                "total": total,
            },
        )

    def test_aggregates_single_day(self) -> None:
        """Test basic aggregation of dropout events into a single day"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T11:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        agg = DropoutAggregate.objects.get(
            exercise_type="word_choice", unit_id=10, dropout_position=3, total_items=10
        )
        self.assertEqual(agg.dropout_count, 2)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate aggregates"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-16T10:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(DropoutAggregate.objects.count(), 2)

    def test_aggregates_different_positions(self) -> None:
        """Test that different dropout positions create separate aggregates"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=2,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=5,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(DropoutAggregate.objects.count(), 2)
        self.assertEqual(
            DropoutAggregate.objects.get(dropout_position=2).dropout_count, 1
        )
        self.assertEqual(
            DropoutAggregate.objects.get(dropout_position=5).dropout_count, 1
        )

    def test_aggregates_different_exercise_types(self) -> None:
        """Test that different exercise types create separate aggregates"""
        self._create_event(
            exercise_type="vocabulary_list",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(DropoutAggregate.objects.count(), 2)

    def test_aggregates_null_unit_id(self) -> None:
        """Test aggregation with null unit_id"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=None,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=None,
            position=3,
            total=10,
            timestamp="2026-01-15T11:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(DropoutAggregate.objects.count(), 1)
        agg = DropoutAggregate.objects.get()
        self.assertIsNone(agg.unit_id)
        self.assertEqual(agg.dropout_count, 2)

    def test_null_and_non_null_unit_id_separate(self) -> None:
        """Test that null and non-null unit_ids create separate aggregates"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=None,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        call_command("aggregate_analytics")

        self.assertEqual(DropoutAggregate.objects.count(), 2)

    def test_increments_existing_aggregate(self) -> None:
        """Test that running twice increments existing aggregates"""
        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        call_command("aggregate_analytics")

        self._create_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T14:00:00",
        )
        call_command("aggregate_analytics")

        agg = DropoutAggregate.objects.get(
            exercise_type="word_choice",
            unit_id=10,
            dropout_position=3,
            total_items=10,
        )
        self.assertEqual(agg.dropout_count, 2)

    def test_no_events(self) -> None:
        """Test that running with no events does nothing"""
        call_command("aggregate_analytics")
        self.assertEqual(DropoutAggregate.objects.count(), 0)
