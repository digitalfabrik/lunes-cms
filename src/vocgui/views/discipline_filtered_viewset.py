from .utils import (
    get_filtered_discipline_queryset,
    get_discipline_by_group_queryset,
    get_overview_discipline_queryset,
)
from rest_framework import viewsets
from vocgui.models import Discipline
from vocgui.serializers import DisciplineSerializer


class DisciplineFilteredViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Discipline module, optionally filtered respected to
    the different mptt levels or a group id.
    If no discipline id is given, all root elements will be displayed.
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
        if "discipline_id" in self.kwargs:
            queryset = get_filtered_discipline_queryset(self)
        elif "group_id" in self.kwargs:
            queryset = get_discipline_by_group_queryset(self)
        else:
            queryset = get_overview_discipline_queryset()
        return queryset
