from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


class AnalyticsEventTests(APITestCase):
    """
    Test class for AnalyticsEvent
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("api:v2:analytics:analytics_event-list")

    def test_unknown_event_type(self) -> None:
        """Test that an unknown event type is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "unknown_event",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
