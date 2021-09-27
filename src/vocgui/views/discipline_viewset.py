from rest_framework import viewsets
from django.db.models import Count, Q
from vocgui.models import Discipline
from vocgui.serializers import DisciplineSerializer

class DisciplineViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Discipline module, optionally filtered by user groups.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DisciplineViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Discipline.objects.none()
        if "group_id" in self.kwargs:
            groups = self.kwargs["group_id"].split("&")
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if obj.get_descendant_count() == 0
                    ]
                )
                & (Q(creator_is_admin=True) | Q(created_by__in=groups))
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
                total_discipline_children=Count("children"),
            )
        else:
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(creator_is_admin=True)
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if obj.get_descendant_count() == 0
                    ]
                )
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
                total_discipline_children=Count("children"),
            )
        return queryset