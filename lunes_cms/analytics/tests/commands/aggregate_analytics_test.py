# pylint: disable=too-many-lines
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from lunes_cms.analytics.models import AnalyticsEvent
from lunes_cms.cmsv2.models import Unit
from lunes_cms.cmsv2.models.job import Job

PATCH_PUSH = "lunes_cms.analytics.management.commands.aggregate_analytics.push_lines"


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

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        self.assertEqual(AnalyticsEvent.objects.count(), 3)
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_job_selection", line)
        self.assertIn(f"job_id={self.job1.id}", line)
        self.assertIn('job_name="Job 1"', line)
        self.assertIn("selection_count=1i", line)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate lines"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(self.job1.id, "add", "2026-01-16T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_aggregates_multiple_jobs(self) -> None:
        """Test that events for different jobs create separate lines"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(self.job2.id, "add", "2026-01-15T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any(f"job_id={self.job1.id}" in l for l in lines))
        self.assertTrue(any(f"job_id={self.job2.id}" in l for l in lines))
        self.assertTrue(all("selection_count=1i" in l for l in lines))

    def test_second_run_pushes_only_new_events(self) -> None:
        """Test that running twice pushes each batch of new events separately"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_called_once()

        self._create_event(self.job1.id, "add", "2026-01-15T14:00:00")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("selection_count=1i", line)

    def test_no_events(self) -> None:
        """Test that running with no events does not push anything"""
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_not_called()

    def test_nonexistent_job_id(self) -> None:
        """Test that events with nonexistent job_ids are pushed with an unknown_<id> tag"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")
        self._create_event(99999, "add", "2026-01-15T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        mock_push.assert_called_once()
        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("job_id=99999" in l for l in lines))
        self.assertTrue(any('job_name="unknown_99999"' in l for l in lines))

    def test_only_removes_count(self) -> None:
        """Test aggregation with only remove actions gives negative count"""
        self._create_event(self.job1.id, "remove", "2026-01-15T10:00:00")
        self._create_event(self.job1.id, "remove", "2026-01-15T11:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("selection_count=-2i", line)

    def test_rolls_back_marking_when_push_fails(self) -> None:
        """If the InfluxDB push fails, the events are not left marked as aggregated"""
        self._create_event(self.job1.id, "add", "2026-01-15T10:00:00")

        with patch(PATCH_PUSH, side_effect=RuntimeError("boom")):
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 1
        )

        # A subsequent run (once InfluxDB is reachable again) picks the event back up.
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )


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

    def test_valid_session_creates_line(self) -> None:
        """A single valid session pair pushes one InfluxDB line"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        self.assertEqual(AnalyticsEvent.objects.count(), 2)
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_sessions", line)
        self.assertIn("total_sessions=1i", line)
        self.assertIn("total_duration_seconds=30i", line)

    def test_multiple_sessions_same_day(self) -> None:
        """Multiple valid sessions on the same day are aggregated into one line"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:10:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=2i", line)
        self.assertIn("total_duration_seconds=630i", line)

    def test_sessions_on_different_days(self) -> None:
        """Sessions on different days create separate lines"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:02:00")
        self._create_session("s2", "2026-01-16T10:00:00", "2026-01-16T10:02:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_second_run_pushes_only_new_sessions(self) -> None:
        """Running the command twice pushes new sessions in each run separately"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_called_once()

        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:00:30")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=1i", line)
        self.assertIn("total_duration_seconds=30i", line)

    def test_does_not_push_on_rerun_with_no_new_events(self) -> None:
        """Re-running with no new events does not push"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:00:30")
        with patch(PATCH_PUSH):
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_not_called()

    def test_pairs_session_across_runs(self) -> None:
        """A session_start in run N and session_end in run N+1 still get paired"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        # Start arrived but no matching end yet -> no push, event left unmarked
        mock_push.assert_not_called()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 1
        )

        self._create_session_event("s1", "session_end", "2026-01-15T10:00:30")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=1i", line)
        self.assertIn("total_duration_seconds=30i", line)
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )

    def test_ignores_start_without_end(self) -> None:
        """A session_start without a matching session_end produces no push"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_not_called()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 1
        )

    def test_ignores_end_without_start(self) -> None:
        """A session_end without a matching session_start produces no push"""
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_not_called()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 1
        )

    def test_ignores_duplicate_start_events(self) -> None:
        """A session_id with two start events and one end event produces no push"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")
        self._create_session_event("s1", "session_start", "2026-01-15T10:01:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_not_called()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 3
        )

    def test_ignores_duplicate_end_events(self) -> None:
        """A session_id with one start event and two end events produces no push"""
        self._create_session_event("s1", "session_start", "2026-01-15T10:00:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:05:00")
        self._create_session_event("s1", "session_end", "2026-01-15T10:06:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_not_called()
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 3
        )

    def test_invalid_sessions_dont_affect_valid_ones(self) -> None:
        """Invalid sessions are discarded but valid ones are still pushed"""
        # Valid session
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:02:00")
        # Invalid: start without end
        self._create_session_event("s2", "session_start", "2026-01-15T11:00:00")
        # Invalid: duplicate starts
        self._create_session_event("s3", "session_start", "2026-01-15T12:00:00")
        self._create_session_event("s3", "session_start", "2026-01-15T12:01:00")
        self._create_session_event("s3", "session_end", "2026-01-15T12:05:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=1i", line)
        self.assertIn("total_duration_seconds=120i", line)
        # The two valid pair events are marked, the four invalid ones remain unmarked
        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 4
        )

    def test_varied_durations_sum_correctly(self) -> None:
        """Sessions with very different durations all contribute to total_duration_seconds"""
        self._create_session("s1", "2026-01-15T10:00:00", "2026-01-15T10:01:00")  # 60s
        self._create_session("s2", "2026-01-15T11:00:00", "2026-01-15T11:01:01")  # 61s
        self._create_session("s3", "2026-01-15T12:00:00", "2026-01-15T12:05:00")  # 300s
        self._create_session("s4", "2026-01-15T13:00:00", "2026-01-15T13:05:01")  # 301s
        self._create_session(
            "s5", "2026-01-15T14:00:00", "2026-01-15T14:30:00"
        )  # 1800s
        self._create_session(
            "s6", "2026-01-15T15:00:00", "2026-01-15T15:31:00"
        )  # 1860s

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=6i", line)
        self.assertIn(
            f"total_duration_seconds={60 + 61 + 300 + 301 + 1800 + 1860}i", line
        )


class ModuleDurationAggregateTests(TestCase):
    """
    Tests for module duration event aggregation.
    """

    def setUp(self) -> None:
        self.unit1 = Unit.objects.create(title="Unit 1")
        self.unit2 = Unit.objects.create(title="Unit 2")

    def _create_standard_event(
        self, exercise_type: str, unit_id: int, timestamp: str, duration_seconds: int
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="module_duration",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": exercise_type,
                    "unit_id": unit_id,
                },
                "duration_seconds": duration_seconds,
            },
        )

    def _create_training_event(
        self, exercise_type: str, job_id: int, timestamp: str, duration_seconds: int
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="module_duration",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "training",
                    "exercise_type": exercise_type,
                    "job_id": job_id,
                },
                "duration_seconds": duration_seconds,
            },
        )

    def test_aggregates_single_day(self) -> None:
        """Test basic aggregation of standard module duration events into a single day"""
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T11:00:00", 90
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_module_duration", line)
        self.assertIn(f"unit_id={self.unit1.id}", line)
        self.assertIn('unit_name="Unit 1"', line)
        self.assertIn("exercise_type=word_choice", line)
        self.assertIn("total_sessions=2i", line)
        self.assertIn("total_duration_seconds=150i", line)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate lines"""
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-16T10:00:00", 60
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_aggregates_different_exercise_types(self) -> None:
        """Test that different exercise types create separate lines"""
        self._create_standard_event(
            "word_list", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("exercise_type=word_list" in l for l in lines))
        self.assertTrue(any("exercise_type=word_choice" in l for l in lines))

    def test_aggregates_different_units(self) -> None:
        """Test that different unit IDs create separate lines"""
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        self._create_standard_event(
            "word_choice", self.unit2.id, "2026-01-15T10:00:00", 90
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(
            any(
                f"unit_id={self.unit1.id}" in l and "total_duration_seconds=60i" in l
                for l in lines
            )
        )
        self.assertTrue(
            any(
                f"unit_id={self.unit2.id}" in l and "total_duration_seconds=90i" in l
                for l in lines
            )
        )

    def test_second_run_pushes_only_new_events(self) -> None:
        """Test that running twice pushes new events in each run separately"""
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        with patch(PATCH_PUSH):
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T14:00:00", 40
        )
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("total_sessions=1i", line)
        self.assertIn("total_duration_seconds=40i", line)

    def test_no_events(self) -> None:
        """Test that running with no events does not push anything"""
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_not_called()

    def test_aggregates_training_exercise(self) -> None:
        """Test aggregation of training module duration events"""
        self._create_training_event("image", 5, "2026-01-15T10:00:00", 120)
        self._create_training_event("image", 5, "2026-01-15T11:00:00", 80)

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("job_id=5", line)
        self.assertIn('job_name="unknown_5"', line)
        self.assertIn("exercise_type=image", line)
        self.assertIn("total_sessions=2i", line)
        self.assertIn("total_duration_seconds=200i", line)

    def test_aggregates_different_training_types(self) -> None:
        """Test that different training exercise types create separate lines"""
        self._create_training_event("image", 5, "2026-01-15T10:00:00", 60)
        self._create_training_event("sentence", 5, "2026-01-15T10:00:00", 60)
        self._create_training_event("speech", 5, "2026-01-15T10:00:00", 60)

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 3)

    def test_aggregates_different_jobs(self) -> None:
        """Test that different job IDs create separate training lines"""
        self._create_training_event("image", 5, "2026-01-15T10:00:00", 60)
        self._create_training_event("image", 6, "2026-01-15T10:00:00", 90)

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(
            any("job_id=5" in l and "total_duration_seconds=60i" in l for l in lines)
        )
        self.assertTrue(
            any("job_id=6" in l and "total_duration_seconds=90i" in l for l in lines)
        )

    def test_standard_and_training_create_separate_lines(self) -> None:
        """Test that standard and training exercises produce separate lines"""
        self._create_standard_event(
            "word_choice", self.unit1.id, "2026-01-15T10:00:00", 60
        )
        self._create_training_event("image", 5, "2026-01-15T10:00:00", 60)

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any(f"unit_id={self.unit1.id}" in l for l in lines))
        self.assertTrue(any("job_id=5" in l for l in lines))


class DropoutAggregateTests(TestCase):
    """
    Tests for exercise dropout event aggregation.
    """

    def _create_standard_event(
        self,
        *,
        exercise_type: str,
        unit_id: int,
        position: int,
        total: int,
        timestamp: str,
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_dropout",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": exercise_type,
                    "unit_id": unit_id,
                },
                "position": position,
                "total": total,
            },
        )

    def _create_training_event(  # pylint: disable=too-many-arguments
        self,
        *,
        exercise_type: str,
        job_id: int,
        position: int,
        total: int,
        timestamp: str,
        vocabulary_item_id: int = 100,
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_dropout",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "training",
                    "exercise_type": exercise_type,
                    "job_id": job_id,
                },
                "position": position,
                "total": total,
                "vocabulary_item_id": vocabulary_item_id,
            },
        )

    def test_aggregates_single_day(self) -> None:
        """Test basic aggregation of dropout events into a single day"""
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T11:00:00",
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_dropout", line)
        self.assertIn("unit_id=10", line)
        self.assertIn("exercise_type=word_choice", line)
        self.assertIn("position=3", line)
        self.assertIn("total=10", line)
        self.assertIn("dropout_count=2i", line)

    def test_aggregates_multiple_days(self) -> None:
        """Test that events on different days create separate lines"""
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-16T10:00:00",
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_aggregates_different_positions(self) -> None:
        """Test that different dropout positions create separate lines"""
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=2,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=5,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(
            any("position=2" in l and "dropout_count=1i" in l for l in lines)
        )
        self.assertTrue(
            any("position=5" in l and "dropout_count=1i" in l for l in lines)
        )

    def test_aggregates_different_exercise_types(self) -> None:
        """Test that different exercise types create separate lines"""
        self._create_standard_event(
            exercise_type="word_list",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_aggregates_training_events_grouped(self) -> None:
        """Test that training events with the same job_id are grouped into one line"""
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
            vocabulary_item_id=99,
        )
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=3,
            total=10,
            timestamp="2026-01-15T11:00:00",
            vocabulary_item_id=99,
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("job_id=5", line)
        self.assertIn("dropout_count=2i", line)

    def test_training_and_standard_events_separate(self) -> None:
        """Test that training events (job) and standard events (unit_id) create separate lines"""
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_second_run_pushes_only_new_events(self) -> None:
        """Test that running twice pushes new events in each run separately"""
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        with patch(PATCH_PUSH):
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T14:00:00",
        )
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("dropout_count=1i", line)

    def test_no_events(self) -> None:
        """Test that running with no events does not push anything"""
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_not_called()

    def test_aggregates_training_dropout(self) -> None:
        """Test aggregation of dropout events for training exercises"""
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=2,
            total=8,
            timestamp="2026-01-15T10:00:00",
            vocabulary_item_id=99,
        )
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=2,
            total=8,
            timestamp="2026-01-15T11:00:00",
            vocabulary_item_id=99,
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        [line] = mock_push.call_args[0][0]
        self.assertIn("job_id=5", line)
        self.assertIn('job_name="unknown_5"', line)
        self.assertIn("exercise_type=image", line)
        self.assertIn("position=2", line)
        self.assertIn("total=8", line)
        self.assertNotIn("vocab_id", line)
        self.assertIn("dropout_count=2i", line)

    def test_different_vocabulary_items_are_aggregated_together(self) -> None:
        """Test that dropouts on different vocabulary items are grouped into one line"""
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=2,
            total=8,
            timestamp="2026-01-15T10:00:00",
            vocabulary_item_id=10,
        )
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=2,
            total=8,
            timestamp="2026-01-15T11:00:00",
            vocabulary_item_id=20,
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 1)
        self.assertIn("dropout_count=2i", lines[0])
        self.assertNotIn("vocab_id", lines[0])

    def test_standard_and_training_dropout_separate(self) -> None:
        """Test that standard and training dropouts produce separate lines"""
        self._create_standard_event(
            exercise_type="word_choice",
            unit_id=10,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
        )
        self._create_training_event(
            exercise_type="image",
            job_id=5,
            position=3,
            total=10,
            timestamp="2026-01-15T10:00:00",
            vocabulary_item_id=99,
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("unit_id=10" in l for l in lines))
        self.assertTrue(any("job_id=5" in l for l in lines))


class ExerciseRepetitionAggregateTests(TestCase):
    """
    Tests for exercise repetition event aggregation.
    """

    def setUp(self) -> None:
        self.job = Job.objects.create(name="Test Job")

    def _create_standard_event(
        self, exercise_type: str, unit_id: int, timestamp: str
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_repetition",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": exercise_type,
                    "unit_id": unit_id,
                },
                "session_id": "session-1",
            },
        )

    def _create_training_event(
        self, exercise_type: str, job_id: int, timestamp: str
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_repetition",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "exercise_key": {
                    "type": "training",
                    "exercise_type": exercise_type,
                    "job_id": job_id,
                },
                "session_id": "session-1",
            },
        )

    def test_aggregates_standard_events_by_day(self) -> None:
        """Multiple standard events from the same session are one bucket with reps=3"""
        self._create_standard_event("word_choice", 10, "2026-01-15T10:00:00")
        self._create_standard_event("word_choice", 10, "2026-01-15T11:00:00")
        self._create_standard_event("word_choice", 10, "2026-01-15T12:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self.assertEqual(
            AnalyticsEvent.objects.filter(aggregated_at__isnull=True).count(), 0
        )
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_exercise_repetition", line)
        self.assertIn("unit_id=10", line)
        self.assertIn("exercise_type=word_choice", line)
        self.assertIn("repetitions_per_session=3", line)
        self.assertIn("session_count=1i", line)
        self.assertNotIn("session_id", line)

    def test_aggregates_different_days(self) -> None:
        """Events on different days create separate lines"""
        self._create_standard_event("word_choice", 10, "2026-01-15T10:00:00")
        self._create_standard_event("word_choice", 10, "2026-01-16T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("repetitions_per_session=1" in l for l in lines))
        self.assertTrue(all("session_count=1i" in l for l in lines))

    def test_aggregates_different_units(self) -> None:
        """Events for different unit_ids create separate lines"""
        self._create_standard_event("word_choice", 10, "2026-01-15T10:00:00")
        self._create_standard_event("word_choice", 20, "2026-01-15T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("unit_id=10" in l for l in lines))
        self.assertTrue(any("unit_id=20" in l for l in lines))

    def test_aggregates_different_exercise_types(self) -> None:
        """Events for different exercise types create separate lines"""
        self._create_standard_event("word_choice", 10, "2026-01-15T10:00:00")
        self._create_standard_event("word_list", 10, "2026-01-15T10:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)

    def test_aggregates_training_events(self) -> None:
        """Training events from the same session are one bucket with reps=2"""
        self._create_training_event("image", self.job.id, "2026-01-15T10:00:00")
        self._create_training_event("image", self.job.id, "2026-01-15T11:00:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_exercise_repetition", line)
        self.assertIn(f"job_id={self.job.id}", line)
        self.assertIn('job_name="Test Job"', line)
        self.assertIn("exercise_type=image", line)
        self.assertIn("repetitions_per_session=2", line)
        self.assertIn("session_count=1i", line)
        self.assertNotIn("session_id", line)

    def test_different_sessions_same_day_same_reps_are_bucketed(self) -> None:
        """Two sessions each doing 1 rep land in the same bucket: session_count=2"""
        AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_repetition",
            timestamp=datetime.fromisoformat("2026-01-15T10:00:00").replace(
                tzinfo=timezone.utc
            ),
            payload={
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": "word_choice",
                    "unit_id": 10,
                },
                "session_id": "session-A",
            },
        )
        AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_repetition",
            timestamp=datetime.fromisoformat("2026-01-15T11:00:00").replace(
                tzinfo=timezone.utc
            ),
            payload={
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": "word_choice",
                    "unit_id": 10,
                },
                "session_id": "session-B",
            },
        )

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        [line] = mock_push.call_args[0][0]
        self.assertIn("repetitions_per_session=1", line)
        self.assertIn("session_count=2i", line)
        self.assertNotIn("session_id", line)

    def test_distribution_buckets_with_different_rep_counts(self) -> None:
        """Sessions with different rep counts produce separate distribution lines"""

        def _make(session_id: str, timestamp: str) -> None:
            AnalyticsEvent.objects.create(
                installation_id="test-install",
                event_type="exercise_repetition",
                timestamp=datetime.fromisoformat(timestamp).replace(
                    tzinfo=timezone.utc
                ),
                payload={
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "word_choice",
                        "unit_id": 10,
                    },
                    "session_id": session_id,
                },
            )

        # session-A: 3 reps
        _make("session-A", "2026-01-15T10:00:00")
        _make("session-A", "2026-01-15T10:01:00")
        _make("session-A", "2026-01-15T10:02:00")
        # session-B: 1 rep
        _make("session-B", "2026-01-15T11:00:00")
        # session-C: 3 reps
        _make("session-C", "2026-01-15T12:00:00")
        _make("session-C", "2026-01-15T12:01:00")
        _make("session-C", "2026-01-15T12:02:00")

        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        lines = mock_push.call_args[0][0]
        self.assertEqual(len(lines), 2)
        self.assertTrue(
            any(
                "repetitions_per_session=3" in l and "session_count=2i" in l
                for l in lines
            )
        )
        self.assertTrue(
            any(
                "repetitions_per_session=1" in l and "session_count=1i" in l
                for l in lines
            )
        )

    def test_second_run_pushes_only_new_events(self) -> None:
        """Running twice pushes new events in each run separately"""
        self._create_standard_event("word_choice", 10, "2026-01-15T10:00:00")
        with patch(PATCH_PUSH):
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        self._create_standard_event("word_choice", 10, "2026-01-15T14:00:00")
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")

        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("repetitions_per_session=1", line)
        self.assertIn("session_count=1i", line)

    def test_no_events(self) -> None:
        """Running with no events does not push anything"""
        with patch(PATCH_PUSH) as mock_push:
            with self.captureOnCommitCallbacks(execute=True):
                call_command("aggregate_analytics")
        mock_push.assert_not_called()


# 829 Enable cleanup
@unittest.skip(
    "Cleanup is temporarily disabled — see issue for re-enabling _delete_old_unprocessed_events"
)
class UnprocessedEventCleanupTests(TestCase):
    """
    Tests for deletion of events not covered by batch aggregators.
    """

    OLD_TIMESTAMP = datetime.now(tz=timezone.utc) - timedelta(days=91)
    RECENT_TIMESTAMP = datetime.now(tz=timezone.utc) - timedelta(days=1)

    def _create_event(self, event_type: str, timestamp: datetime) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type=event_type,
            timestamp=timestamp,
            payload={},
        )

    def test_deletes_old_exercise_repetition_events(self) -> None:
        """exercise_repetition events older than 90 days are deleted"""
        self._create_event("exercise_repetition", self.OLD_TIMESTAMP)

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_keeps_recent_exercise_repetition_events(self) -> None:
        """exercise_repetition events within 90 days are kept"""
        self._create_event("exercise_repetition", self.RECENT_TIMESTAMP)

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 1)

    def test_deletes_old_unknown_event_types(self) -> None:
        """Events of unknown type older than 90 days are deleted"""
        self._create_event("unknown_future_type", self.OLD_TIMESTAMP)

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)

    def test_keeps_recent_unknown_event_types(self) -> None:
        """Events of unknown type within 90 days are kept"""
        self._create_event("unknown_future_type", self.RECENT_TIMESTAMP)

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 1)
