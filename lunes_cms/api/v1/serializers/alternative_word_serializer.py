from rest_framework import serializers

from ....cms.models import AlternativeWord


class AlternativeWordSerializer(serializers.ModelSerializer):
    """
    Serializer for the AlternativeWord module. Inherits from
    `serializers.ModelSerializer`.
    """

    article = serializers.IntegerField(source="singular_article")

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = AlternativeWord
        fields = ("alt_word", "article")
