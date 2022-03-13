from rest_framework import viewsets
from django.db.models import F, Q, Count
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
            return None
        else:
            queryset = Discipline.objects.filter(
                released=True, creator_is_admin=True, lft=F("rght") - 1
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
                total_discipline_children=Count("children"),
            )
        return queryset
