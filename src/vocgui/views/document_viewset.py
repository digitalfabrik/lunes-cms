from rest_framework import viewsets
from vocgui.models import Document
from vocgui.serializers import DocumentSerializer
from vocgui.models import TrainingSet
from .utils import check_group_object_permissions


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Document module.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    serializer_class = DocumentSerializer
    http_method_names = ["get"]

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
        group_id = TrainingSet.objects.filter(
            id=self.kwargs["training_set_id"]
        ).values_list("created_by_id", flat=True)[0]
        if group_id:
            check_group_object_permissions(self.request, group_id)
        queryset = (
            Document.objects.filter(
                training_sets__id=self.kwargs["training_set_id"],
                document_image__confirmed=True,
            )
            .select_related()
            .distinct()
            .order_by("word")
        )
        return queryset
