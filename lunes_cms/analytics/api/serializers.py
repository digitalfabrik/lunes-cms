from __future__ import annotations

from typing import Any

from rest_framework import serializers

from ..models import AnalyticsEvent

STANDARD_EXERCISE_TYPES = [
    AnalyticsEvent.ExerciseType.WORD_LIST,
    AnalyticsEvent.ExerciseType.WORD_CHOICE,
]
TRAINING_EXERCISE_TYPES = [
    AnalyticsEvent.ExerciseType.IMAGE,
    AnalyticsEvent.ExerciseType.SENTENCE,
    AnalyticsEvent.ExerciseType.SPEECH,
]


class PayloadSerializer(serializers.Serializer):
    """Common base class for all payload serializers"""

    def update(self, instance: Any, validated_data: Any) -> Any:
        raise RuntimeError("Should not be called on a payload serializer")

    def create(self, validated_data: Any) -> Any:
        raise RuntimeError("Should not be called on a payload serializer")


class StandardExerciseKeySerializer(PayloadSerializer):
    """Validates the exercise key for a standard (unit-based) exercise"""

    type = serializers.ChoiceField(choices=[AnalyticsEvent.ExerciseKeyType.STANDARD])
    exercise_type = serializers.ChoiceField(choices=STANDARD_EXERCISE_TYPES)
    unit_id = serializers.IntegerField()


class TrainingExerciseKeySerializer(PayloadSerializer):
    """Validates the exercise key for a training (job-based) exercise"""

    type = serializers.ChoiceField(choices=[AnalyticsEvent.ExerciseKeyType.TRAINING])
    exercise_type = serializers.ChoiceField(choices=TRAINING_EXERCISE_TYPES)
    job_id = serializers.IntegerField()


_EXERCISE_KEY_SUB_SERIALIZERS: dict[str, type[PayloadSerializer]] = {
    AnalyticsEvent.ExerciseKeyType.STANDARD: StandardExerciseKeySerializer,
    AnalyticsEvent.ExerciseKeyType.TRAINING: TrainingExerciseKeySerializer,
}


class ExerciseKeySerializer(PayloadSerializer):
    """
    Validates an exercise_key payload field.
    Reads the 'type' field first, then delegates to StandardExerciseKeySerializer
    or TrainingExerciseKeySerializer to validate the remaining fields.
    """

    def to_internal_value(self, data: Any) -> dict:
        key_type = data.get("type") if isinstance(data, dict) else None
        if key_type not in _EXERCISE_KEY_SUB_SERIALIZERS:
            raise serializers.ValidationError(
                {"type": f'Must be one of: {", ".join(_EXERCISE_KEY_SUB_SERIALIZERS)}.'}
            )
        sub_serializer = _EXERCISE_KEY_SUB_SERIALIZERS[key_type](data=data)
        if not sub_serializer.is_valid():
            raise serializers.ValidationError(sub_serializer.errors)
        return sub_serializer.validated_data


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

    exercise_key = ExerciseKeySerializer()
    duration_seconds = serializers.IntegerField()


class ExerciseDropoutPayloadSerializer(PayloadSerializer):
    """Validates the payload of an exercise_dropout analytics event"""

    exercise_key = ExerciseKeySerializer()
    position = serializers.IntegerField()
    total = serializers.IntegerField()
    vocabulary_item_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        if (
            attrs["exercise_key"]["type"] == AnalyticsEvent.ExerciseKeyType.TRAINING
            and attrs.get("vocabulary_item_id") is None
        ):
            raise serializers.ValidationError(
                {"vocabulary_item_id": "This field is required for training exercises."}
            )
        return attrs


class ExerciseRepetitionPayloadSerializer(PayloadSerializer):
    """
    Validates the payload of an exercise_repetition analytics event
    """

    exercise_key = ExerciseKeySerializer()
    session_id = serializers.CharField(max_length=32)


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
