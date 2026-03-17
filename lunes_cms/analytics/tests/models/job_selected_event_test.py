from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from lunes_cms.analytics.models import AnalyticsEvent


class JobSelectedEventTests(APITestCase):
    """
    Test class for job_selected analytics events
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("api:v2:analytics:analytics_event-list")
        self.valid_payload = {
            "installation_id": "test123",
            "event_type": "job_selected",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {"job_id": 1, "action": "add"},
        }

    def test_create_valid_event(self) -> None:
        """Test creating a valid job_selected event"""
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "job_selected")
        self.assertEqual(event.payload["job_id"], 1)
        self.assertEqual(event.payload["action"], "add")

    def test_remove_action(self) -> None:
        """Test creating a job_selected event with remove action"""
        payload = {**self.valid_payload, "payload": {"job_id": 1, "action": "remove"}}
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 201)

    def test_invalid_action(self) -> None:
        """Test that an invalid action is rejected"""
        payload = {**self.valid_payload, "payload": {"job_id": 1, "action": "invalid"}}
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_job_id(self) -> None:
        """Test that a missing job_id is rejected"""
        payload = {**self.valid_payload, "payload": {"action": "add"}}
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        payload = {k: v for k, v in self.valid_payload.items() if k != "payload"}
        response = self.client.post(self.url, data=payload, format="json")
        self.assertEqual(response.status_code, 400)
