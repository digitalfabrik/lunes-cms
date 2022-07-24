from django.db.models import Count, Q

from rest_framework import viewsets

from ....cms.models import Discipline, TrainingSet
from ...utils import check_group_object_permissions
from ..serializers import TrainingSetSerializer


class TrainingSetViewSet(viewsets.ModelViewSet):
    """
    List training sets.
    If discipline ID is provided as a parameter,
    the list will return only training sets belonging to the discipline.
    A valid API-Key may be required.
    """

    serializer_class = TrainingSetSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`TrainingSetViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return TrainingSet.objects.none()
        discipline_infos = Discipline.objects.filter(
            id=self.kwargs["discipline_id"]
        ).values_list("created_by_id", "creator_is_admin")
        group_id = discipline_infos[0][0]
        is_admin = discipline_infos[0][1]
        if group_id and not is_admin:
            check_group_object_permissions(self.request, group_id)
        queryset = TrainingSet.objects.filter(
            discipline__id=self.kwargs["discipline_id"], released=True
        ).annotate(
            total_documents=Count(
                "documents",
                filter=Q(documents__document_image__confirmed=True),
                distinct=True,
            )
        )
        return queryset
