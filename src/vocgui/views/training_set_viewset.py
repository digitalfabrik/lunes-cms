from rest_framework import viewsets
from django.db.models import Count, Q
from vocgui.models import TrainingSet
from vocgui.serializers import TrainingSetSerializer


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
        user = self.request.user
        queryset = (
            TrainingSet.objects.filter(
                discipline__id=self.kwargs["discipline_id"], released=True
            )
            .order_by("order")
            .annotate(
                total_documents=Count(
                    "documents", filter=Q(documents__document_image__confirmed=True)
                )
            )
        )
        return queryset
