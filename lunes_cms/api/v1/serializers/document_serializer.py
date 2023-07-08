from rest_framework import serializers

from ....cms.models import Document
from .alternative_word_serializer import AlternativeWordSerializer
from .document_image_serializer import DocumentImageSerializer


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Document module. Inherits from
    `serializers.ModelSerializer`.
    """

    alternatives = AlternativeWordSerializer(many=True, read_only=True)
    document_image = DocumentImageSerializer(many=True, read_only=True)

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Document
        fields = (
            "id",
            "word",
            "article",
            "audio",
            "word_type",
            "alternatives",
            "document_image",
            "example_sentence",
        )
