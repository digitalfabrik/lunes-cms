from django.urls import reverse
from rest_framework.test import APITestCase

from lunes_cms.analytics.models import AnalyticsEvent


class AnalyticsEventTests(APITestCase):
    """
    Test class for AnalyticsEvent
    """

    def setUp(self) -> None:
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

    def test_missing_payload(self) -> None:
        """Test that a missing payload is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "job_selected",
                "timestamp": "2026-01-30T12:34:56Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_job_selected_event(self) -> None:
        """Test creating a valid job_selected event"""
        response = self.client.post(
            self.url,
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
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "job_selected")
        self.assertEqual(event.payload["job_id"], 1)
        self.assertEqual(event.payload["action"], "add")

    def test_job_selected_remove_action(self) -> None:
        """Test creating a job_selected event with remove action"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "job_selected",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"job_id": 1, "action": "remove"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_job_selected_invalid_action(self) -> None:
        """Test that an invalid action is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "job_selected",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"job_id": 1, "action": "invalid"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_job_selected_missing_job_id(self) -> None:
        """Test that a missing job_id is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "job_selected",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"action": "add"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_module_duration_event(self) -> None:
        """Test creating a valid module_duration event for a standard exercise"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "module_duration",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "word_choice",
                        "unit_id": 1,
                    },
                    "duration_seconds": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "module_duration")
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "word_choice")
        self.assertEqual(event.payload["exercise_key"]["unit_id"], 1)
        self.assertEqual(event.payload["duration_seconds"], 10)

    def test_create_training_module_duration_event(self) -> None:
        """Test creating a valid module_duration event for a training exercise"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "module_duration",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "training",
                        "exercise_type": "image",
                        "job_id": 5,
                    },
                    "duration_seconds": 45,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "image")
        self.assertEqual(event.payload["exercise_key"]["job_id"], 5)

    def test_create_session_start_event(self) -> None:
        """Test creating a valid session_start event"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "session_start",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"session_id": "abc123"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "session_start")
        self.assertEqual(event.payload["session_id"], "abc123")

    def test_create_session_end_event(self) -> None:
        """Test creating a valid session_end event"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "session_end",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {"session_id": "abc123"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "session_end")
        self.assertEqual(event.payload["session_id"], "abc123")

    def test_create_exercise_dropout_event(self) -> None:
        """Test creating a valid exercise_dropout event for a standard exercise"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "word_choice",
                        "unit_id": 5,
                    },
                    "position": 3,
                    "total": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AnalyticsEvent.objects.count(), 1)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.event_type, "exercise_dropout")
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "word_choice")
        self.assertEqual(event.payload["exercise_key"]["unit_id"], 5)
        self.assertEqual(event.payload["position"], 3)
        self.assertEqual(event.payload["total"], 10)

    def test_create_training_exercise_dropout_event(self) -> None:
        """Test creating a valid exercise_dropout event for a training exercise"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "training",
                        "exercise_type": "sentence",
                        "job_id": 7,
                    },
                    "position": 2,
                    "total": 6,
                    "vocabulary_item_id": 42,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.first()
        assert event is not None
        self.assertEqual(event.payload["exercise_key"]["exercise_type"], "sentence")
        self.assertEqual(event.payload["exercise_key"]["job_id"], 7)
        self.assertEqual(event.payload["vocabulary_item_id"], 42)

    def test_training_exercise_dropout_missing_vocabulary_item_id(self) -> None:
        """Test that a training exercise dropout without vocabulary_item_id is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "training",
                        "exercise_type": "sentence",
                        "job_id": 7,
                    },
                    "position": 2,
                    "total": 6,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_standard_exercise_dropout_without_vocabulary_item_id(self) -> None:
        """Test that a standard exercise dropout without vocabulary_item_id is accepted"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "word_choice",
                        "unit_id": 5,
                    },
                    "position": 3,
                    "total": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_exercise_dropout_invalid_exercise_key_type(self) -> None:
        """Test that an invalid exercise_key type is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "unknown",
                        "exercise_type": "word_choice",
                        "unit_id": 5,
                    },
                    "position": 3,
                    "total": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_exercise_dropout_invalid_exercise_type_for_standard(self) -> None:
        """Test that a training exercise_type is rejected for a standard exercise_key"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "image",
                        "unit_id": 5,
                    },
                    "position": 3,
                    "total": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_exercise_dropout_missing_position(self) -> None:
        """Test that a missing position field is rejected"""
        response = self.client.post(
            self.url,
            data={
                "installation_id": "test123",
                "event_type": "exercise_dropout",
                "timestamp": "2026-01-30T12:34:56Z",
                "payload": {
                    "exercise_key": {
                        "type": "exercise",
                        "exercise_type": "word_choice",
                        "unit_id": 5,
                    },
                    "total": 10,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
