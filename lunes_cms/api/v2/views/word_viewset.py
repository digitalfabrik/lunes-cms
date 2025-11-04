from django.db.models import Q
from rest_framework import viewsets

from ....cmsv2.models import Word
from ..serializers import WordSerializer


class WordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words with their default images, or a single word by id
    """

    serializer_class = WordSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of words/documents

        :return: The queryset of words
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Word.objects.none()

        queryset = Word.objects.filter(
            unit_word_relations__unit__released=True,
            unit_word_relations__unit__jobs__released=True,
            audio_check_status="CONFIRMED",
            image_check_status="CONFIRMED",
        ).filter(
            Q(example_sentence="")
            | Q(
                example_sentence_check_status="CONFIRMED", example_sentence_audio__gt=""
            )
        )
        return queryset.distinct().order_by("word")
