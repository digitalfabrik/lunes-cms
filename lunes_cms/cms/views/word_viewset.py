from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from ..models import Document
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
        return (
            Document.objects.filter(
                creator_is_admin=True,
                document_image__confirmed=True,
                training_sets__released=True,
                training_sets__discipline__released=True,
            )
            .select_related()
            .distinct()
        )
