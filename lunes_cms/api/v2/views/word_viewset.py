from rest_framework import viewsets

from ..matomo_tracking import matomo_tracking
from ..serializers import WordSerializer
from ....cmsv2.models import Word


class WordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words with their default images, or a single word by id
    """

    serializer_class = WordSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All words")
    def list(self, request, *args, **kwargs):
        """List all words with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    @matomo_tracking(action_name="Word", resource_id="pk")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single word with Matomo tracking."""
        return super().retrieve(request, *args, **kwargs)

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
        )
        return queryset.distinct().order_by("word")
