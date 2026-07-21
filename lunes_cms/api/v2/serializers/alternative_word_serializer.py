from __future__ import annotations

from rest_framework import serializers

from ....cmsv2.models import AlternativeWord


class AlternativeWordSerializer(serializers.ModelSerializer):
    """
    Serializer for alternative words.
    """

    article = serializers.CharField(source="singular_article_as_text")

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = AlternativeWord
        fields = ("alt_word", "article")
