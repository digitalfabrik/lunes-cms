from rest_framework import serializers

from ....cms.models import TrainingSet
from .fallback_icon_serializer import FallbackIconSerializer


class TrainingSetSerializer(FallbackIconSerializer):
    """
    Serializer for the TrainingSet module. Inherits from
    `FallbackIconSerializer`.
    """

    total_documents = serializers.IntegerField()

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = TrainingSet
        fields = ("id", "title", "description", "icon", "total_documents")
