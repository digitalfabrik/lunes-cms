from rest_framework import serializers

from ....cmsv2.models.unit import UnitWordRelation
from ...utils import build_absolute_url


class UnitWordRelationSerializer(serializers.ModelSerializer):
    """
    Serializer for unit word relations.
    """

    id = serializers.IntegerField(source="word.id")
    word = serializers.CharField(source="word.word")
    article = serializers.CharField(source="word.singular_article_as_text")
    images = serializers.ListSerializer(
        child=serializers.ImageField(), source="effective_public_images"
    )
    audio = serializers.FileField(source="word.audio")
    example_sentence = serializers.SerializerMethodField()
    example_sentence_audio = serializers.SerializerMethodField()

    def get_example_sentence(self, obj):
        """
        Return the example sentence from the relation if it exists with audio and confirmed status,
        otherwise fallback to the word's example sentence with the same requirements.
        Return None if neither relation nor word has a valid example sentence.
        """
        # Check relation's example sentence
        if (
            obj.example_sentence
            and obj.example_sentence_audio
            and obj.example_sentence_check_status == "CONFIRMED"
        ):
            return obj.example_sentence

        # Fallback to word's example sentence
        if (
            obj.word.example_sentence
            and obj.word.example_sentence_audio
            and obj.word.example_sentence_check_status == "CONFIRMED"
        ):
            return obj.word.example_sentence

        return None

    def get_example_sentence_audio(self, obj):
        """
        Return the example sentence audio from the relation if it exists with sentence and confirmed status,
        otherwise fallback to the word's example sentence audio with the same requirements.
        """
        url = None

        # Check relation's example sentence audio
        if (
            obj.example_sentence
            and obj.example_sentence_audio
            and obj.example_sentence_check_status == "CONFIRMED"
        ):
            url = (
                obj.example_sentence_audio.url
                if hasattr(obj.example_sentence_audio, "url")
                else obj.example_sentence_audio
            )
        # Fallback to word's example sentence audio
        elif (
            obj.word.example_sentence
            and obj.word.example_sentence_audio
            and obj.word.example_sentence_check_status == "CONFIRMED"
        ):
            url = (
                obj.word.example_sentence_audio.url
                if hasattr(obj.word.example_sentence_audio, "url")
                else obj.word.example_sentence_audio
            )

        return build_absolute_url(self.context, url)

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = UnitWordRelation
        fields = (
            "id",
            "word",
            "article",
            "images",
            "audio",
            "example_sentence",
            "example_sentence_audio",
        )
