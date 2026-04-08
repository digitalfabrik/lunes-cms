from datetime import datetime, timezone

from django.core.management import call_command
from django.test import TestCase

from lunes_cms.analytics.models import AnalyticsEvent, ExerciseRepetitionAggregate


class ExerciseRepetitionAggregateTests(TestCase):
    """
    Tests for aggregation of exercise_repetition events.
    """

    def _create_event(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        unit_id: int,
        exercise_type: str,
        repetition_count: int,
        start_count: int,
        date: str,
        timestamp: str = "2026-01-15T10:00:00",
    ) -> AnalyticsEvent:
        return AnalyticsEvent.objects.create(
            installation_id="test-install",
            event_type="exercise_repetition",
            timestamp=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
            payload={
                "unit_id": unit_id,
                "exercise_type": exercise_type,
                "repetition_count": repetition_count,
                "start_count": start_count,
                "date": date,
            },
        )

    def test_aggregates_multiple_repetition_events_for_same_key(self) -> None:
        """Test that multiple events for the same unit/exercise/date are merged into one aggregate"""
        self._create_event(1, "word_choice", 3, 1, "2026-01-15")
        self._create_event(1, "word_choice", 5, 2, "2026-01-15")

        call_command("aggregate_analytics")

        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, exercise_type="word_choice", date="2026-01-15"
        )
        self.assertEqual(aggregate.repetition_count, 8)
        self.assertEqual(aggregate.start_count, 3)

    def test_different_dates_create_separate_repetition_aggregates(self) -> None:
        """Test that the same unit/exercise on different dates creates separate records"""
        self._create_event(1, "word_choice", 3, 1, "2026-01-15")
        self._create_event(1, "word_choice", 3, 1, "2026-01-16")

        call_command("aggregate_analytics")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_different_exercise_types_create_separate_repetition_aggregates(
        self,
    ) -> None:
        """Test that different exercise types create separate aggregate records"""
        self._create_event(1, "word_choice", 3, 1, "2026-01-15")
        self._create_event(1, "article_choice", 3, 1, "2026-01-15")

        call_command("aggregate_analytics")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_different_units_create_separate_repetition_aggregates(self) -> None:
        """Test that different units create separate aggregate records"""
        self._create_event(1, "word_choice", 3, 1, "2026-01-15")
        self._create_event(2, "word_choice", 3, 1, "2026-01-15")

        call_command("aggregate_analytics")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_increments_existing_repetition_aggregate(self) -> None:
        """Test that running the command twice increments existing aggregates"""
        self._create_event(1, "word_choice", 3, 1, "2026-01-15")
        call_command("aggregate_analytics")

        self._create_event(1, "word_choice", 2, 1, "2026-01-15")
        call_command("aggregate_analytics")

        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, exercise_type="word_choice", date="2026-01-15"
        )
        self.assertEqual(aggregate.repetition_count, 5)
        self.assertEqual(aggregate.start_count, 2)

    def test_no_repetition_events(self) -> None:
        """Test that running with no events does nothing"""
        call_command("aggregate_analytics")
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)
