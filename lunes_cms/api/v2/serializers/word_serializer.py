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
        )
