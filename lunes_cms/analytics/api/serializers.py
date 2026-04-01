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


class SessionStartPayloadSerializer(PayloadSerializer):
    """Validates the payload of a session start analytics event"""

    session_id = serializers.CharField(max_length=32)


class SessionEndPayloadSerializer(PayloadSerializer):
    """Validates the payload of a session end analytics event"""

    session_id = serializers.CharField(max_length=32)


class ModuleDurationPayloadSerializer(PayloadSerializer):
    """Validates the payload of a module duration analytics event"""

    exercise_type = serializers.ChoiceField(
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    unit_id = serializers.IntegerField()
    duration_seconds = serializers.IntegerField()


class ExerciseDropoutPayloadSerializer(PayloadSerializer):
    """Validates the payload of an exercise_dropout analytics event"""

    exercise_type = serializers.ChoiceField(
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    unit_id = serializers.IntegerField(allow_null=True)
    position = serializers.IntegerField()
    total = serializers.IntegerField()


class ExerciseRepetitionPayloadSerializer(PayloadSerializer):
    """
    Validates the payload of an exercise_repetition analytics event
    """

    exercise_type = serializers.ChoiceField(
        choices=AnalyticsEvent.ExerciseType.choices,
    )
    unit_id = serializers.IntegerField()
    repetition_count = serializers.IntegerField()
    start_count = serializers.IntegerField()
    date = serializers.DateField()


EVENT_PAYLOAD_SERIALIZERS: dict[str, type[serializers.Serializer]] = {
    AnalyticsEvent.EventType.JOB_SELECTED: JobSelectedPayloadSerializer,
    AnalyticsEvent.EventType.SESSION_START: SessionStartPayloadSerializer,
    AnalyticsEvent.EventType.SESSION_END: SessionEndPayloadSerializer,
    AnalyticsEvent.EventType.MODULE_DURATION: ModuleDurationPayloadSerializer,
    AnalyticsEvent.EventType.EXERCISE_DROPOUT: ExerciseDropoutPayloadSerializer,
    AnalyticsEvent.EventType.EXERCISE_REPETITION: ExerciseRepetitionPayloadSerializer,
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
