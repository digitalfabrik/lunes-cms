from rest_framework import serializers

from ....cmsv2.models import Word


class WordSerializer(serializers.ModelSerializer):
    """
    Serializer for Words.
    """

    article = serializers.CharField(source="singular_article_as_text")

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Word
        fields = (
            "id",
            "word",
            "article",
            "image",
            "audio",
        )
