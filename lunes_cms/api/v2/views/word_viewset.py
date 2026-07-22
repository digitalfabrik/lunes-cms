from __future__ import annotations

from typing import Any

from django.db.models import Prefetch, QuerySet
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from ....cmsv2.models import Word
from ....cmsv2.models.unit import UnitWordRelation
from ..matomo_tracking import matomo_tracking
from ..serializers import WordSerializer

#: The minimum length a ``search`` term has to have
MIN_SEARCH_LENGTH = 3


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Case-insensitive substring the returned words have to contain "
                "(at least 3 characters, otherwise the request is rejected with "
                "HTTP 400). When given, all public images of a word are returned, "
                "including the images defined on its released unit relations (not "
                "only the word's default image)."
            ),
        )
    ]
)
class WordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all words with their default images, or a single word by id.

    Supports an optional ``search`` query parameter that keeps only the words whose
    term contains the given string (case-insensitive). The term has to be at least
    three characters long, otherwise the request is rejected with HTTP 400. When
    searching, the returned images include the images defined on the word's released
    unit relations in addition to the word's default image.
    """

    serializer_class = WordSerializer
    http_method_names = ["get"]

    @matomo_tracking(action_name="All words")
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """List all words with Matomo tracking."""
        return super().list(request, *args, **kwargs)

    @matomo_tracking(action_name="Word", resource_id="pk")
    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Retrieve a single word with Matomo tracking."""
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Word]:
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

        search = self.request.query_params.get("search")
        if search is not None:
            search = search.strip()
            if len(search) < MIN_SEARCH_LENGTH:
                raise ValidationError(
                    {
                        "search": _(
                            "The search term has to be at least %(min)d characters long."
                        )
                        % {"min": MIN_SEARCH_LENGTH}
                    }
                )
            queryset = queryset.filter(word__icontains=search)
            # When searching we expose all public images of a word, so prefetch the
            # images of its released unit relations into the attribute that
            # ``Word.images_for_api`` reads from.
            public_relations = (
                UnitWordRelation.objects.filter(
                    unit__released=True,
                    unit__jobs__released=True,
                    word__audio_check_status="CONFIRMED",
                    image_check_status="CONFIRMED",
                )
                .exclude(image="")
                .order_by("unit__title")
            )
            queryset = queryset.prefetch_related(
                Prefetch(
                    "unit_word_relations",
                    public_relations,
                    to_attr="unit_word_relations_of_job",
                )
            )

        return queryset.distinct().order_by("word")
