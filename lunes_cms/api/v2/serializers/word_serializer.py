from __future__ import annotations

from typing import Optional

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ....cmsv2.models import Word
from ...utils import build_absolute_url
from .alternative_word_serializer import AlternativeWordSerializer


class WordSerializer(serializers.ModelSerializer):
    """
    Serializer for Words.
    """

    article = serializers.CharField(source="singular_article_as_text")
    alternative_words = AlternativeWordSerializer(many=True, read_only=True)
    images = serializers.ListSerializer(
        child=serializers.ImageField(), source="images_for_api"
    )
    example_sentence = serializers.SerializerMethodField()
    example_sentence_audio = serializers.SerializerMethodField()
    migrated = serializers.SerializerMethodField()

    def get_example_sentence(self, obj: Word) -> Optional[str]:
        """Return None for empty example sentences instead of empty string and if it's not confirmed."""
        if (
            obj.example_sentence
            and obj.example_sentence_audio
            and obj.example_sentence_check_status == "CONFIRMED"
        ):
            return obj.example_sentence
        return None

    def get_example_sentence_audio(self, obj: Word) -> Optional[str]:
        """
        Return None for example sentence audio if it's not confirmed.
        :param obj: The word object
        :return None or example sentence audio if it's confirmed.
        """
        if (
            obj.example_sentence_audio
            and obj.example_sentence
            and obj.example_sentence_check_status == "CONFIRMED"
        ):
            url: str = (
                obj.example_sentence_audio.url
                if hasattr(obj.example_sentence_audio, "url")
                else str(obj.example_sentence_audio)
            )
            return build_absolute_url(self.context, url)
        return None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_migrated(self, obj: Word) -> bool:
        """Return True if the word was migrated from the old data model"""
        return obj.v1_id is not None

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Word
        fields = (
            "id",
            "word",
            "article",
            "alternative_words",
            "images",
            "audio",
            "example_sentence",
            "example_sentence_audio",
            "migrated",
        )
