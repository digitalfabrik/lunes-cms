from rest_framework import viewsets
from django.db.models import Count, Q
from vocgui.models import TrainingSet
from vocgui.serializers import TrainingSetSerializer
from vocgui.models import Discipline
from .utils import check_group_object_permissions


class TrainingSetViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the TrainingSet module.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
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
        group_id = Discipline.objects.filter(
            id=self.kwargs["discipline_id"]
        ).values_list("created_by_id", flat=True)[0]
        if group_id:
            check_group_object_permissions(self.request, group_id)
        queryset = (
            TrainingSet.objects.filter(
                discipline__id=self.kwargs["discipline_id"], released=True
            )
            .order_by("order")
            .annotate(
                total_documents=Count(
                    "documents",
                    filter=Q(documents__document_image__confirmed=True),
                    distinct=True,
                )
            )
        )
        return queryset
