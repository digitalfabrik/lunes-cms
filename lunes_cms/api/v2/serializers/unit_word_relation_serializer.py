from rest_framework import serializers

from ....cmsv2.models.unit import UnitWordRelation


class UnitWordRelationSerializer(serializers.ModelSerializer):
    """
    Serializer for unit word relations.
    """

    id = serializers.IntegerField(source="word.id")
    word = serializers.CharField(source="word.word")
    article = serializers.CharField(source="word.singular_article_as_text")
    image = serializers.ImageField(source="effective_public_image")
    audio = serializers.FileField(source="word.audio")

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = UnitWordRelation
        fields = (
            "id",
            "word",
            "article",
            "image",
            "audio",
        )
