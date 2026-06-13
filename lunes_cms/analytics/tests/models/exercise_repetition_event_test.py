from typing import Any
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from lunes_cms.analytics.models import AnalyticsEvent

PATCH_PUSH = "lunes_cms.analytics.api.views.push_lines"


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
        with patch(PATCH_PUSH):
            response = self.client.post(
                self.url, data=self.valid_standard_payload, format="json"
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "exercise_repetition")
        self.assertEqual(event.payload["exercise_key"]["unit_id"], 1)
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "word_choice")
        self.assertEqual(event.payload["session_id"], "session-1")

    def test_creates_standard_aggregate_immediately(self) -> None:
        """Test that posting a standard event immediately pushes to InfluxDB"""
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(
                self.url, data=self.valid_standard_payload, format="json"
            )
        self.assertEqual(response.status_code, 201)
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_exercise_repetition", line)
        self.assertIn("unit_id=1", line)
        self.assertIn("exercise_type=word_choice", line)
        self.assertIn("session_id=session-1", line)
        self.assertIn("repetition_count=1i", line)

    def test_repeated_standard_events_each_push_once(self) -> None:
        """Test that multiple standard events for the same key each push repetition_count=1i"""
        with patch(PATCH_PUSH) as mock_push:
            self.client.post(self.url, data=self.valid_standard_payload, format="json")
            self.client.post(self.url, data=self.valid_standard_payload, format="json")
            self.client.post(self.url, data=self.valid_standard_payload, format="json")

        self.assertEqual(mock_push.call_count, 3)
        for call in mock_push.call_args_list:
            [line] = call[0][0]
            self.assertIn("repetition_count=1i", line)

    def test_create_valid_training_event(self) -> None:
        """Test creating a valid training exercise_repetition event"""
        with patch(PATCH_PUSH):
            response = self.client.post(
                self.url, data=self.valid_training_payload, format="json"
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.payload["exercise_key"]["job_id"], 42)
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "image")

    def test_creates_training_aggregate_immediately(self) -> None:
        """Test that posting a training event immediately pushes to InfluxDB"""
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(
                self.url, data=self.valid_training_payload, format="json"
            )
        self.assertEqual(response.status_code, 201)
        mock_push.assert_called_once()
        [line] = mock_push.call_args[0][0]
        self.assertIn("lunes_exercise_repetition", line)
        self.assertIn("job=unknown_42", line)
        self.assertIn("exercise_type=image", line)
        self.assertIn("session_id=session-1", line)
        self.assertIn("repetition_count=1i", line)

    def test_repeated_training_events_each_push_once(self) -> None:
        """Test that multiple training events for the same key each push repetition_count=1i"""
        with patch(PATCH_PUSH) as mock_push:
            self.client.post(self.url, data=self.valid_training_payload, format="json")
            self.client.post(self.url, data=self.valid_training_payload, format="json")

        self.assertEqual(mock_push.call_count, 2)
        for call in mock_push.call_args_list:
            [line] = call[0][0]
            self.assertIn("repetition_count=1i", line)

    def test_standard_and_training_push_different_tags(self) -> None:
        """Test that standard and training events push with different dimension tags"""
        with patch(PATCH_PUSH) as mock_push:
            self.client.post(self.url, data=self.valid_standard_payload, format="json")
            self.client.post(self.url, data=self.valid_training_payload, format="json")

        self.assertEqual(mock_push.call_count, 2)
        lines = [call[0][0][0] for call in mock_push.call_args_list]
        self.assertTrue(any("unit_id=1" in l for l in lines))
        self.assertTrue(any("job=unknown_42" in l for l in lines))

    def test_different_sessions_push_different_tags(self) -> None:
        """Test that events with different session_ids push with different session tags"""
        payload_session2 = {
            **self.valid_standard_payload,
            "payload": {
                **self.valid_standard_payload["payload"],
                "session_id": "session-2",
            },
        }
        with patch(PATCH_PUSH) as mock_push:
            self.client.post(self.url, data=self.valid_standard_payload, format="json")
            self.client.post(self.url, data=payload_session2, format="json")

        self.assertEqual(mock_push.call_count, 2)
        lines = [call[0][0][0] for call in mock_push.call_args_list]
        self.assertTrue(any("session_id=session-1" in l for l in lines))
        self.assertTrue(any("session_id=session-2" in l for l in lines))

    def test_different_units_push_different_tags(self) -> None:
        """Test that different unit_ids push with different unit tags"""
        payload_unit2 = {
            **self.valid_standard_payload,
            "payload": {
                **self.valid_standard_payload["payload"],
                "exercise_key": {
                    **self.valid_standard_payload["payload"]["exercise_key"],
                    "unit_id": 2,
                },
            },
        }
        with patch(PATCH_PUSH) as mock_push:
            self.client.post(self.url, data=self.valid_standard_payload, format="json")
            self.client.post(self.url, data=payload_unit2, format="json")

        self.assertEqual(mock_push.call_count, 2)
        lines = [call[0][0][0] for call in mock_push.call_args_list]
        self.assertTrue(any("unit_id=1" in l for l in lines))
        self.assertTrue(any("unit_id=2" in l for l in lines))

    def test_missing_exercise_key(self) -> None:
        """Test that a missing exercise_key is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {"session_id": "session-1"},
        }
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()

    def test_invalid_exercise_key_type(self) -> None:
        """Test that an invalid exercise_key type is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {
                "exercise_key": {
                    "type": "unknown",
                    "exercise_type": "word_choice",
                    "unit_id": 1,
                },
                "session_id": "session-1",
            },
        }
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()

    def test_missing_unit_id_for_standard_key(self) -> None:
        """Test that a standard exercise_key without unit_id is rejected"""
        payload = {
            **self.valid_standard_payload,
            "payload": {
                "exercise_key": {"type": "exercise", "exercise_type": "word_choice"},
                "session_id": "session-1",
            },
        }
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()

    def test_missing_job_id_for_training_key(self) -> None:
        """Test that a training exercise_key without job_id is rejected"""
        payload = {
            **self.valid_training_payload,
            "payload": {
                "exercise_key": {"type": "training", "exercise_type": "image"},
                "session_id": "session-1",
            },
        }
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()

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
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        payload = {
            key: value
            for key, value in self.valid_standard_payload.items()
            if key != "payload"
        }
        with patch(PATCH_PUSH) as mock_push:
            response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
        mock_push.assert_not_called()
