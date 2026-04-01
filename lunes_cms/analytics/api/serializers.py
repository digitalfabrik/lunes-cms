from typing import Any

from rest_framework import serializers

from ..models import AnalyticsEvent


class JobSelectedPayloadSerializer(
    serializers.Serializer
):  # pylint: disable=abstract-method
    """
    Validates the payload of a job_selected analytics event
    """

    job_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["add", "remove"])


class ModuleDurationPayloadSerializer(
    serializers.Serializer
):  # pylint: disable=abstract-method
    """
    Validates the payload of a module_duration analytics event
    """

    exercise_type = serializers.IntegerField()
    unit_id = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()


class SessionPayloadSerializer(
    serializers.Serializer
):  # pylint: disable=abstract-method
    """
    Validates the payload of a session_start or session_end analytics event
    """

    session_id = serializers.CharField()


EVENT_PAYLOAD_SERIALIZERS: dict[str, type[serializers.Serializer]] = {
    AnalyticsEvent.EventType.JOB_SELECTED: JobSelectedPayloadSerializer,
    AnalyticsEvent.EventType.MODULE_DURATION: ModuleDurationPayloadSerializer,
    AnalyticsEvent.EventType.SESSION_START: SessionPayloadSerializer,
    AnalyticsEvent.EventType.SESSION_END: SessionPayloadSerializer,
}


class AnalyticsEventSerializer(serializers.ModelSerializer):
    """
    Serializer for analytics events. Payload validation is dispatched based on event_type.
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        payload_serializer = EVENT_PAYLOAD_SERIALIZERS[attrs["event_type"]](
            data=attrs["payload"]
        )
        if not payload_serializer.is_valid():
            raise serializers.ValidationError({"payload": payload_serializer.errors})
        return attrs

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = AnalyticsEvent
        fields = ("installation_id", "event_type", "timestamp", "payload")
