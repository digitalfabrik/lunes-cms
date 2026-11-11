from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.contrib.auth import get_user
from django.db.models import Prefetch, QuerySet
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from ....bildschatz.access import may_use_bildschatz
from ....cmsv2.areas import published_units, published_words
from ....cmsv2.models import Unit, Word
from ....cmsv2.models.unit import UnitWordRelation
from ..matomo_tracking import matomo_tracking
from ..serializers import WordSerializer
from .area_scoped_mixin import AreaScopedMixin

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

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
                "only the word's default image). Until Bildschatz is released to the "
                "public, searching requires a login to the CMS (HTTP 403 otherwise)."
            ),
        )
    ]
)
class WordViewSet(AreaScopedMixin, viewsets.ModelViewSet):
    """
    Retrieve the list of all words with their default images, or a single word by id.

    Without an area access token these are the words of the main app, with one
    they are the words of that area.

    Supports an optional ``search`` query parameter that keeps only the words whose
    term contains the given string (case-insensitive). The term has to be at least
    three characters long, otherwise the request is rejected with HTTP 400. When
    searching, the returned images include the images defined on the word's released
    unit relations in addition to the word's default image. Until Bildschatz is
    released to the public, searching requires a login to the CMS, otherwise the
    request is rejected with HTTP 403.
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

    def _session_user(self) -> AbstractBaseUser | AnonymousUser:
        """
        The user logged in to the CMS in this browser session.

        The API itself only knows area tokens, but the Bildschatz website calls it
        from the same site, so the session cookie of a CMS login comes along. The
        user is read from the session rather than from the request, because the
        REST framework replaces the user of the request with the result of its own
        authentication.

        :return: The logged in user, or an anonymous user
        """
        # pylint: disable=protected-access
        return get_user(self.request._request)

    def get_queryset(self) -> QuerySet[Word]:
        """
        Get the queryset of words/documents

        :return: The queryset of words
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Word.objects.none()

        area = self.area
        assert area is not None
        queryset = published_words(
            Word.objects.filter(
                unit_word_relations__unit__released=True,
                unit_word_relations__unit__jobs__released=True,
                unit_word_relations__unit__jobs__archived=False,
                audio_check_status="CONFIRMED",
                image_check_status="CONFIRMED",
            ),
            area,
        )

        search = self.request.query_params.get("search")
        if search is not None:
            if not may_use_bildschatz(self._session_user()):
                raise PermissionDenied(
                    _("Searching words requires a login to the CMS.")
                )
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
            # ``Word.images_for_api`` reads from. Only units the API publishes for
            # this area are considered, so no image of another area or of an
            # archived job leaks.
            public_units = published_units(
                Unit.objects.filter(
                    released=True,
                    jobs__released=True,
                    jobs__archived=False,
                ),
                area,
            )
            public_relations = (
                UnitWordRelation.objects.filter(
                    unit__in=public_units,
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

        return (
            queryset.prefetch_related("alternative_words").distinct().order_by("word")
        )
