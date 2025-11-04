from django.db.models import Q, OuterRef, Prefetch, Exists
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from ....cmsv2.models import Job, Word
from ..serializers import WordSerializer
from ....cmsv2.models.unit import UnitWordRelation


class JobWordsViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words of a job.
    A word is returned if it public in at least one unit that belongs to the job.
    All public images that belong to a public unit of that job will be returned.
    Images of relations are ordered alphabetically by their unit title
    and the default image of the word always comes last.
    """

    serializer_class = WordSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of words

        :return: The queryset of words
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Word.objects.none()

        try:
            job = Job.objects.get(id=self.kwargs["job_id"])
        except Job.DoesNotExist as e:
            raise PermissionDenied() from e

        if not job.released:
            raise PermissionDenied()

        unit_word_relations = (
            UnitWordRelation.objects.filter(
                unit__released=True,
                unit__jobs=job,
                word__audio_check_status="CONFIRMED",
            )
            .filter(
                Q(image_check_status="CONFIRMED")
                | Q(image="", word__image_check_status="CONFIRMED")
            )
            .filter(
                Q(example_sentence="")
                | Q(
                    example_sentence_check_status="CONFIRMED",
                    example_sentence_audio__gt="",
                )
                | Q(
                    word__example_sentence__gt="",
                    word__example_sentence_check_status="CONFIRMED",
                    word__example_sentence_audio__gt="",
                )
            )
        )
        queryset = (
            Word.objects.filter(
                Exists(unit_word_relations.filter(word__id=OuterRef("id")))
            )
            .prefetch_related(
                Prefetch(
                    "unit_word_relations",
                    unit_word_relations.exclude(image="").order_by("unit__title"),
                    to_attr="unit_word_relations_of_job",
                )
            )
            .order_by("word")
        )

        return queryset
