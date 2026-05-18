from typing import Any

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from lunes_cms.analytics.models import AnalyticsEvent, ExerciseRepetitionAggregate


class ExerciseRepetitionEventTests(APITestCase):
    """
    Test class for exercise_repetition analytics events
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("api:v2:analytics:analytics_event-list")
        self.valid_payload: dict[str, Any] = {
            "installation_id": "test123",
            "event_type": "exercise_repetition",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {
                "unit_id": 1,
                "exercise_type": "word_choice",
                "session_id": "session-1",
            },
        }

    def test_create_valid_event(self) -> None:
        """Test creating a valid exercise_repetition event"""
        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "exercise_repetition")
        self.assertEqual(event.payload["unit_id"], 1)
        self.assertEqual(event.payload["exercise_type"], "word_choice")
        self.assertEqual(event.payload["session_id"], "session-1")

    def test_creates_aggregate_immediately(self) -> None:
        """Test that posting an event immediately creates an aggregate with repetition_count=1"""
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, exercise_type="word_choice", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 1)

    def test_repeated_events_increment_repetition_count(self) -> None:
        """Test that multiple events for the same unit/exercise/session increment the count"""
        self.client.post(self.url, data=self.valid_payload, format="json")
        self.client.post(self.url, data=self.valid_payload, format="json")
        self.client.post(self.url, data=self.valid_payload, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 1)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, exercise_type="word_choice", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 3)

    def test_different_sessions_create_separate_aggregates(self) -> None:
        """Test that events with different session_ids create separate aggregates"""
        self.client.post(self.url, data=self.valid_payload, format="json")
        payload_session2 = {
            **self.valid_payload,
            "payload": {**self.valid_payload["payload"], "session_id": "session-2"},
        }
        self.client.post(self.url, data=payload_session2, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_different_units_create_separate_aggregates(self) -> None:
        """Test that different units for the same exercise/session create separate aggregates"""
        self.client.post(self.url, data=self.valid_payload, format="json")
        payload_unit2 = {
            **self.valid_payload,
            "payload": {**self.valid_payload["payload"], "unit_id": 2},
        }
        self.client.post(self.url, data=payload_unit2, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_missing_unit_id(self) -> None:
        """Test that a missing unit_id is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "exercise_type": "word_choice",
                "session_id": "session-1",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_exercise_type(self) -> None:
        """Test that a missing exercise_type is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "unit_id": 1,
                "session_id": "session-1",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_session_id(self) -> None:
        """Test that a missing session_id is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "unit_id": 1,
                "exercise_type": "word_choice",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        payload = {
            key: value for key, value in self.valid_payload.items() if key != "payload"
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)
