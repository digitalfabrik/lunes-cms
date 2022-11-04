from django.db.models import Q

from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from ....cms.models import Document, GroupAPIKey
from ...utils import get_key
from ..serializers import DocumentSerializer


class WordViewSet(viewsets.ModelViewSet):
    """
    Retrieve the list of all default words/documents or get a single record by appending the id of the requested word.
    """

    serializer_class = DocumentSerializer
    http_method_names = ["get"]
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def get_queryset(self):
        """
        Get the queryset of words/documents

        :return: The queryset of words
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        # Get base queryset
        queryset = Document.objects.filter(
            document_image__confirmed=True,
            training_sets__released=True,
            training_sets__discipline__released=True,
        )
        # Get API key of current request
        key = get_key(self.request)
        if key:
            # If the key is given, get the corresponding group
            api_key_object = GroupAPIKey.get_from_token(key)
            # Return all public words as well as those of the group with the given key
            queryset = queryset.filter(
                Q(creator_is_admin=True) | Q(created_by=api_key_object.group)
            )
        else:
            # If no key is given, return all public words
            queryset = queryset.filter(creator_is_admin=True)
        return (
            queryset.select_related().distinct()
            # Sort queryset to make output order deterministic for testing
            .order_by("id")
        )
