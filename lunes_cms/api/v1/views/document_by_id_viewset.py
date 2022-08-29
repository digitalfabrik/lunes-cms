from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from ....cms.models import Document
from ..serializers import DocumentSerializer


class DocumentByIdViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Document module of a given id.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    serializer_class = DocumentSerializer
    http_method_names = ["get"]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DocumentViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        user = self.request.user
        queryset = Document.objects.filter(id=self.kwargs["document_id"])
        return queryset
