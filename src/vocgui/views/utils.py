from django.db.models import Count, Q
from vocgui.models import Discipline
from vocgui.utils import get_child_count
from django.core.exceptions import PermissionDenied
from vocgui.utils import get_key
from vocgui.models import GroupAPIKey


def get_filtered_discipline_queryset(discipline_view_set):
    """Filters

    :param discipline_view_set: A handle to the :class:`DisciplineViewSet`
    :type discipline_view_set: class
    :return: (filtered) queryset
    :rtype: QuerySet
    """
    queryset = Discipline.objects.filter(
        Q(released=True)
        & Q(
            id__in=Discipline.objects.get(
                id=discipline_view_set.kwargs["discipline_id"]
            ).get_children()
        )
    ).annotate(
        total_training_sets=Count(
            "training_sets", filter=Q(training_sets__released=True)
        ),
    )
    queryset = get_non_empty_disciplines(queryset)
    return queryset


def get_overview_discipline_queryset():
    """Returns the general disciplines created by super users if the are
    root nodes and recursively either has at least one sub-discipline or one
    training set. Additionally, they need to be released by the creator group.

    :return: (filtered) queryset
    :rtype: QuerySet
    """
    queryset = Discipline.objects.filter(
        Q(released=True) & Q(creator_is_admin=True)
    ).annotate(
        total_training_sets=Count(
            "training_sets", filter=Q(training_sets__released=True)
        ),
    )
    queryset = [obj for obj in queryset if obj.is_root_node()]
    queryset = get_non_empty_disciplines(queryset)
    return queryset


def get_discipline_by_group_queryset(discipline_view_set):
    """Returns overview of disciplines for a given group id, which must be
    in the keyword arguments of the passed discipline view set. All elements are
    root nodes and recursively either have at least one sub-discipline or one
    training set. Additionally, they need to be released by the creator group.

    :param discipline_view_set: A handle to the :class:`DisciplineViewSet`
    :type discipline_view_set: class
    :return: (filtered) queryset
    :rtype: QuerySet
    """
    queryset = Discipline.objects.filter(
        Q(released=True)
        & Q(created_by=discipline_view_set.kwargs["group_id"])
        & Q(
            id__in=[
                obj.id
                for obj in Discipline.objects.all()
                if get_child_count(obj)
                + obj.training_sets.filter(released=True).count()
                > 0
            ]
        )
    ).annotate(
        total_training_sets=Count(
            "training_sets", filter=Q(training_sets__released=True)
        ),
    )
    queryset = [obj for obj in queryset if obj.is_root_node()]
    return queryset


def get_non_empty_disciplines(queryset):
    """
    Filters a discipline queryset so that every element recursively either have
    at least one sub-discipline or one training set.

    :param queryset: Queryset of `vocgui.Discipline` objects
    :type queryset: QuerySet
    :return: (filtered) queryset
    :rtype: QuerySet
    """
    queryset = [
        obj
        for obj in queryset
        if get_child_count(obj) > 0
        or obj.training_sets.filter(released=True).count() > 0
    ]
    return queryset


def check_group_object_permissions(request, group_id):
    key = get_key(request)
    if not key:
        raise PermissionDenied()
    api_key_object = GroupAPIKey.objects.get_from_key(key)
    if int(api_key_object.organization_id) != int(group_id):
        raise PermissionDenied()
