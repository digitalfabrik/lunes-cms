from rest_framework import serializers

from ....cms.models import DocumentImage
from .document_image_list_serializer import DocumentImageListSerializer


class DocumentImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the DocumentImage module. Inherits from
    `serializers.ModelSerializer`.
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

        list_serializer_class = DocumentImageListSerializer
        model = DocumentImage
        fields = ("id", "image")
