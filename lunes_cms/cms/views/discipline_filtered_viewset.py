from rest_framework import viewsets

from ..models import Discipline
from ..serializers import DisciplineSerializer
from .utils import (
    get_filtered_discipline_queryset,
    get_discipline_by_group_queryset,
    get_overview_discipline_queryset,
    check_group_object_permissions,
)


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
            discipline_infos = Discipline.objects.filter(
                id=self.kwargs["discipline_id"]
            ).values_list("created_by_id", "creator_is_admin")
            group_id = discipline_infos[0][0]
            is_admin = discipline_infos[0][1]
            if group_id and not is_admin:
                check_group_object_permissions(self.request, group_id)
            queryset = get_filtered_discipline_queryset(self)
        elif "group_id" in self.kwargs:
            check_group_object_permissions(self.request, self.kwargs["group_id"])
            queryset = get_discipline_by_group_queryset(self)
        else:
            queryset = get_overview_discipline_queryset()
        return queryset
