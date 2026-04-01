from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from lunes_cms.analytics.models import AnalyticsEvent


class ExerciseRepetitionEventTests(APITestCase):
    """
    Test class for exercise_repetition analytics events
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("api:v2:analytics:analytics_event-list")
        self.valid_payload = {
            "installation_id": "test123",
            "event_type": "exercise_repetition",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {
                "unit_id": 1,
                "exercise_type": "word_choice",
                "repetition_count": 5,
                "start_count": 3,
                "date": "2023-01-30",
            },
        }

    def test_create_valid_event(self) -> None:
        """Test creating a valid exercise_repetition event"""
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "exercise_repetition")
        self.assertEqual(event.payload["unit_id"], 1)
        self.assertEqual(event.payload["exercise_type"], "word_choice")
        self.assertEqual(event.payload["repetition_count"], 5)
        self.assertEqual(event.payload["start_count"], 3)
        self.assertEqual(event.payload["date"], "2023-01-30")

    def test_missing_unit_id(self) -> None:
        """Test that a missing unit_id is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "exercise_type": "word_choice",
                "repetition_count": 5,
                "start_count": 3,
                "date": "2023-01-30",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_exercise_type(self) -> None:
        """Test that a missing exercise_type is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "unit_id": 1,
                "repetition_count": 5,
                "start_count": 3,
                "date": "2023-01-30",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_repetition_count(self) -> None:
        """Test that a missing repetition_count is rejected"""
        payload = {
            **self.valid_payload,
            "payload": {
                "unit_id": 1,
                "exercise_type": "word_choice",
                "start_count": 3,
                "date": "2023-01-30",
            },
        }
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        payload = {k: v for k, v in self.valid_payload.items() if k != "payload"}
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
