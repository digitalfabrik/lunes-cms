from django.db.models import Count, Q
from vocgui.models import Discipline
from vocgui.utils import get_child_count

def get_filtered_discipline_queryset(discipline_view_set):
    queryset = Discipline.objects.filter(
        Q(released=True)
        & Q(creator_is_admin=True)
        & Q(
            id__in=Discipline.objects.get(
                id=discipline_view_set.kwargs["discipline_id"]
            ).get_children()
        )
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
    return queryset

def get_overview_discipline_queryset(discipline_view_set):
    queryset = Discipline.objects.filter(
        Q(released=True)
        & Q(creator_is_admin=True)
    ).annotate(
        total_training_sets=Count(
            "training_sets", filter=Q(training_sets__released=True)
        ),
    )
    queryset = [obj for obj in queryset if obj.is_root_node()]
    queryset = get_non_empty_disciplines(queryset)
    return queryset

def get_discipline_by_group_queryset(discipline_view_set):
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
    return queryset

def get_non_empty_disciplines(queryset):
    queryset = [obj for obj in queryset if get_child_count(obj) > 0 or obj.training_sets.filter(released=True).count() > 0]
    return queryset