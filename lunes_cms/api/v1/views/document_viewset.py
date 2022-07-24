from rest_framework import viewsets

from ....cms.models import Document, TrainingSet
from ...utils import check_group_object_permissions
from ..serializers import DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    """
    List of available documents.
    A document is an item to be learned and consists of an image,
    multiple correct answers, and other details.
    If training set ID is provided as a parameter,
    the list will return only documents belonging to the training set.
    A valid API-Key may be required.
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
        training_set_infos = TrainingSet.objects.filter(
            id=self.kwargs["training_set_id"]
        ).values_list("created_by_id", "creator_is_admin")
        group_id = training_set_infos[0][0]
        is_admin = training_set_infos[0][1]
        if group_id and not is_admin:
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
