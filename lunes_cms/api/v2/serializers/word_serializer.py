from rest_framework import serializers

from ....cmsv2.models import Word


class WordSerializer(serializers.ModelSerializer):
    """
    Serializer for Words.
    """

    article = serializers.CharField(source="singular_article_as_text")
    images = serializers.ListSerializer(
        child=serializers.ImageField(), source="images_for_api"
    )
    example_sentence = serializers.SerializerMethodField()

    def get_example_sentence(self, obj):
        """Return None for empty example sentences instead of empty string."""
        return obj.example_sentence if obj.example_sentence else None

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Word
        fields = (
            "id",
            "word",
            "article",
            "images",
            "audio",
            "example_sentence",
            "example_sentence_audio",
        )
