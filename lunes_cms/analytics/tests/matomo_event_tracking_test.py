from unittest.mock import MagicMock, patch

from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from lunes_cms.analytics.matomo_event_tracking import (
    EVENT_NAME_BUILDERS,
    MatomoEventData,
    forward_analytics_event_to_matomo,
    send_matomo_event,
)
from lunes_cms.analytics.models import AnalyticsEvent


class EventNameBuildersTest(APITestCase):
    """Tests for EVENT_NAME_BUILDERS mapping."""

    def test_job_selected(self) -> None:
        """Test job_selected builds correct event name"""
        name, value = EVENT_NAME_BUILDERS["job_selected"](
            {"job_id": 42, "action": "add"}
        )
        self.assertEqual(name, "job:42:add")
        self.assertIsNone(value)

    def test_session_start(self) -> None:
        """Test session_start builds correct event name"""
        name, value = EVENT_NAME_BUILDERS["session_start"]({"session_id": "abc123"})
        self.assertEqual(name, "session:abc123")
        self.assertIsNone(value)

    def test_session_end(self) -> None:
        """Test session_end builds correct event name"""
        name, value = EVENT_NAME_BUILDERS["session_end"]({"session_id": "abc123"})
        self.assertEqual(name, "session:abc123")
        self.assertIsNone(value)

    def test_module_duration(self) -> None:
        """Test module_duration builds correct event name and value"""
        name, value = EVENT_NAME_BUILDERS["module_duration"](
            {"unit_id": 5, "exercise_type": 1, "duration_seconds": 120}
        )
        self.assertEqual(name, "unit:5:exercise:1")
        self.assertEqual(value, 120.0)

    def test_exercise_dropout(self) -> None:
        """Test exercise_dropout builds correct event name and value"""
        name, value = EVENT_NAME_BUILDERS["exercise_dropout"](
            {
                "exercise_type": "word_choice",
                "unit_id": 5,
                "position": 3,
                "total": 10,
            }
        )
        self.assertEqual(name, "unit:5:exercise:word_choice:pos:3/10")
        self.assertEqual(value, 3.0)

    def test_exercise_dropout_null_unit(self) -> None:
        """Test exercise_dropout uses 'unknown' when unit_id is null"""
        name, value = EVENT_NAME_BUILDERS["exercise_dropout"](
            {
                "exercise_type": "article_choice",
                "unit_id": None,
                "position": 1,
                "total": 5,
            }
        )
        self.assertEqual(name, "unit:unknown:exercise:article_choice:pos:1/5")
        self.assertEqual(value, 1.0)


class SendMatomoEventTest(APITestCase):
    """Tests for send_matomo_event function."""

    @patch("lunes_cms.analytics.matomo_event_tracking.urllib_request.urlopen")
    def test_sends_correct_params(self, mock_urlopen) -> None:
        """Test that send_matomo_event sends correct query params"""
        mock_urlopen.return_value.__enter__ = MagicMock()
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        data = MatomoEventData(
            matomo_url="https://matomo.example.com",
            site_id="1",
            token="secret",
            url="https://app.example.com/api/v2/analytics/events/",
            user_agent="TestAgent/1.0",
            event_category="analytics",
            event_action="job_selected",
            event_name="job:42:add",
            event_value=None,
            os="Android",
            os_version="14",
            app_version="2024.3.0",
        )

        send_matomo_event(data)

        mock_urlopen.assert_called_once()
        request_obj = mock_urlopen.call_args[0][0]
        url = request_obj.full_url

        self.assertIn("matomo.php", url)
        self.assertIn("idsite=1", url)
        self.assertIn("e_c=analytics", url)
        self.assertIn("e_a=job_selected", url)
        self.assertIn("e_n=job%3A42%3Aadd", url)
        self.assertNotIn("e_v=", url)
        self.assertIn("token_auth=secret", url)
        self.assertIn("dimension1=Android", url)
        self.assertIn("dimension2=14", url)
        self.assertIn("dimension3=2024.3.0", url)

    @patch("lunes_cms.analytics.matomo_event_tracking.urllib_request.urlopen")
    def test_includes_event_value(self, mock_urlopen) -> None:
        """Test that event value is included and empty token is omitted"""
        mock_urlopen.return_value.__enter__ = MagicMock()
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        data = MatomoEventData(
            matomo_url="https://matomo.example.com",
            site_id="1",
            token="",
            url="https://app.example.com/api/v2/analytics/events/",
            user_agent="TestAgent/1.0",
            event_category="analytics",
            event_action="module_duration",
            event_name="unit:5:exercise:1",
            event_value=120.0,
        )

        send_matomo_event(data)

        request_obj = mock_urlopen.call_args[0][0]
        url = request_obj.full_url
        self.assertIn("e_v=120.0", url)
        self.assertNotIn("token_auth=", url)


class ForwardAnalyticsEventTest(APITestCase):
    """Tests for forward_analytics_event_to_matomo function."""

    @override_settings(MATOMO_TRACKING=False, MATOMO_URL="", MATOMO_SITE_ID="")
    @patch("lunes_cms.analytics.matomo_event_tracking.executor")
    def test_skipped_when_disabled(self, mock_executor) -> None:
        """Test that forwarding is skipped when MATOMO_TRACKING is False"""
        request = MagicMock()
        forward_analytics_event_to_matomo(
            "job_selected", {"job_id": 1, "action": "add"}, request
        )
        mock_executor.submit.assert_not_called()

    @override_settings(
        MATOMO_TRACKING=True,
        MATOMO_URL="https://matomo.example.com",
        MATOMO_SITE_ID="1",
        MATOMO_TOKEN="secret",
    )
    @patch("lunes_cms.analytics.matomo_event_tracking.executor")
    def test_submits_to_executor(self, mock_executor) -> None:
        """Test that forwarding submits to the thread pool executor"""
        request = MagicMock()
        request.build_absolute_uri.return_value = (
            "https://app.example.com/api/v2/analytics/events/"
        )
        request.META = {"HTTP_USER_AGENT": "TestAgent/1.0"}

        forward_analytics_event_to_matomo(
            "job_selected", {"job_id": 42, "action": "add"}, request
        )

        mock_executor.submit.assert_called_once()
        args = mock_executor.submit.call_args
        self.assertEqual(args[0][0], send_matomo_event)
        data = args[0][1]
        self.assertEqual(data.event_category, "analytics")
        self.assertEqual(data.event_action, "job_selected")
        self.assertEqual(data.event_name, "job:42:add")

    @override_settings(
        MATOMO_TRACKING=True,
        MATOMO_URL="https://matomo.example.com",
        MATOMO_SITE_ID="1",
        MATOMO_TOKEN="",
    )
    @patch("lunes_cms.analytics.matomo_event_tracking.executor")
    def test_unknown_event_type_not_submitted(self, mock_executor) -> None:
        """Test that unknown event types are not forwarded"""
        request = MagicMock()
        forward_analytics_event_to_matomo("unknown_type", {}, request)
        mock_executor.submit.assert_not_called()


class IntegrationTest(APITestCase):
    """Integration test: POST event -> DB record + Matomo forwarding."""

    @override_settings(
        MATOMO_TRACKING=True,
        MATOMO_URL="https://matomo.example.com",
        MATOMO_SITE_ID="1",
        MATOMO_TOKEN="secret",
    )
    @patch("lunes_cms.analytics.matomo_event_tracking.executor")
    def test_post_event_saves_and_forwards(self, mock_executor) -> None:
        """Test that POST creates DB record and forwards to Matomo"""
        url = reverse("api:v2:analytics:analytics_event-list")
        response = self.client.post(
            url,
            data={
                "installation_id": "test123",
                "event_type": "job_selected",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"job_id": 1, "action": "add"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)

        mock_executor.submit.assert_called_once()
        data = mock_executor.submit.call_args[0][1]
        self.assertEqual(data.event_action, "job_selected")
        self.assertEqual(data.event_name, "job:1:add")
