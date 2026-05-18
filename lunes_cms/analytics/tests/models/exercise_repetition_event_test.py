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
        self.valid_standard_payload: dict[str, Any] = {
            "installation_id": "test123",
            "event_type": "exercise_repetition",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": "word_choice",
                    "unit_id": 1,
                },
                "session_id": "session-1",
            },
        }
        self.valid_training_payload: dict[str, Any] = {
            "installation_id": "test123",
            "event_type": "exercise_repetition",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {
                "exercise_key": {
                    "type": "training",
                    "exercise_type": "image",
                    "job_id": 42,
                },
                "session_id": "session-1",
            },
        }

    def test_create_valid_standard_event(self) -> None:
        """Test creating a valid standard exercise_repetition event"""
        self.assertEqual(AnalyticsEvent.objects.count(), 0)
        response = self.client.post(self.url, data=self.valid_standard_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "exercise_repetition")
        self.assertEqual(event.payload["exercise_key"]["unit_id"], 1)
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "word_choice")
        self.assertEqual(event.payload["session_id"], "session-1")

    def test_creates_standard_aggregate_immediately(self) -> None:
        """Test that posting a standard event immediately creates an aggregate"""
        response = self.client.post(self.url, data=self.valid_standard_payload, format="json")
        self.assertEqual(response.status_code, 201)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, job_id=None, exercise_type="word_choice", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 1)

    def test_repeated_standard_events_increment_repetition_count(self) -> None:
        """Test that multiple standard events for the same key increment the count"""
        self.client.post(self.url, data=self.valid_standard_payload, format="json")
        self.client.post(self.url, data=self.valid_standard_payload, format="json")
        self.client.post(self.url, data=self.valid_standard_payload, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 1)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=1, exercise_type="word_choice", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 3)

    def test_create_valid_training_event(self) -> None:
        """Test creating a valid training exercise_repetition event"""
        response = self.client.post(self.url, data=self.valid_training_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.payload["exercise_key"]["job_id"], 42)
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "image")

    def test_creates_training_aggregate_immediately(self) -> None:
        """Test that posting a training event immediately creates an aggregate"""
        response = self.client.post(self.url, data=self.valid_training_payload, format="json")
        self.assertEqual(response.status_code, 201)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            unit_id=None, job_id=42, exercise_type="image", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 1)

    def test_repeated_training_events_increment_repetition_count(self) -> None:
        """Test that multiple training events for the same key increment the count"""
        self.client.post(self.url, data=self.valid_training_payload, format="json")
        self.client.post(self.url, data=self.valid_training_payload, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 1)
        aggregate = ExerciseRepetitionAggregate.objects.get(
            job_id=42, exercise_type="image", session_id="session-1"
        )
        self.assertEqual(aggregate.repetition_count, 2)

    def test_standard_and_training_create_separate_aggregates(self) -> None:
        """Test that standard and training events create separate aggregates"""
        self.client.post(self.url, data=self.valid_standard_payload, format="json")
        self.client.post(self.url, data=self.valid_training_payload, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_different_sessions_create_separate_aggregates(self) -> None:
        """Test that events with different session_ids create separate aggregates"""
        self.client.post(self.url, data=self.valid_standard_payload, format="json")
        payload_session2 = {
            **self.valid_standard_payload,
            "payload": {**self.valid_standard_payload["payload"], "session_id": "session-2"},
        }
        self.client.post(self.url, data=payload_session2, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_different_units_create_separate_aggregates(self) -> None:
        """Test that different unit_ids for the same exercise/session create separate aggregates"""
        self.client.post(self.url, data=self.valid_standard_payload, format="json")
        payload_unit2 = {
            **self.valid_standard_payload,
            "payload": {
                **self.valid_standard_payload["payload"],
                "exercise_key": {**self.valid_standard_payload["payload"]["exercise_key"], "unit_id": 2},
            },
        }
        self.client.post(self.url, data=payload_unit2, format="json")

        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 2)

    def test_missing_exercise_key(self) -> None:
        """Test that a missing exercise_key is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {"session_id": "session-1"},
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_invalid_exercise_key_type(self) -> None:
        """Test that an invalid exercise_key type is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {
                "exercise_key": {"type": "unknown", "exercise_type": "word_choice", "unit_id": 1},
                "session_id": "session-1",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_unit_id_for_standard_key(self) -> None:
        """Test that a standard exercise_key without unit_id is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {
                "exercise_key": {"type": "exercise", "exercise_type": "word_choice"},
                "session_id": "session-1",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_job_id_for_training_key(self) -> None:
        """Test that a training exercise_key without job_id is rejected"""
        payload = {
            **self.valid_training_payload,
            "payload": {
                "exercise_key": {"type": "training", "exercise_type": "image"},
                "session_id": "session-1",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_session_id(self) -> None:
        """Test that a missing session_id is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {
                "exercise_key": {
                    "type": "exercise",
                    "exercise_type": "word_choice",
                    "unit_id": 1,
                },
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        payload = {
            key: value
            for key, value in self.valid_standard_payload.items()
            if key != "payload"
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExerciseRepetitionAggregate.objects.count(), 0)
