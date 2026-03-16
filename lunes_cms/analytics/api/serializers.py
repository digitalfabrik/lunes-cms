from typing import Any

from rest_framework import serializers

from ..models import AnalyticsEvent


class PayloadSerializer(serializers.Serializer):
    """Common base class for all payload serializers"""

    def update(self, instance, validated_data):
        raise RuntimeError("Should not be called on a payload serializer")

    def create(self, validated_data):
        raise RuntimeError("Should not be called on a payload serializer")


class JobSelectedPayloadSerializer(PayloadSerializer):
    """
    Validates the payload of a job_selected analytics event
    """

    job_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["add", "remove"])


EVENT_PAYLOAD_SERIALIZERS: dict[str, type[serializers.Serializer]] = {
    AnalyticsEvent.EventType.JOB_SELECTED: JobSelectedPayloadSerializer,
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
