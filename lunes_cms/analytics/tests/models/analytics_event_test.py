from rest_framework.test import APIClient, APITestCase
from django.urls import reverse

from lunes_cms.analytics.models import AnalyticsEvent


class AnalyticsEventTests(APITestCase):
    """
    Test class for AnalyticsEvent
    """

    def set_up(self) -> None:
        """
        Setup test client
        :return:
        """
        self.client = APIClient()
        self.url = reverse("api:v2:analytics:analytics_event-list")
        self.valid_payload = {
            "installation_id": "test123",
            "event_type": "start",
            "timestamp": "2026-01-30T12:34:56Z",
            "payload": {"foo": "bar"},
        }

    def test_create_valid_event(self) -> None:
        """
        Test creating an event
        """
        response = self.client.post(self.url, data=self.valid_payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        self.assertEqual(event.installation_id, "test123")
