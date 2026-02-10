from rest_framework import serializers

from ..models import AnalyticsEvent


class AnalyticsEventSerializer(serializers.ModelSerializer):
    """
    Serializer class
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = AnalyticsEvent
        fields = (
            "installation_id",
            "event_type",
            "timestamp",
            "payload",
        )
