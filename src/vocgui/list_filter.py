from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from django.utils.translation import ugettext as _

from .models import Discipline, TrainingSet, Document


class DocumentDisciplineListFilter(admin.SimpleListFilter):
    """
    This filter will always return a subset of the instances in a Model, either filtering by the
    user choice or by a default value.
    """

    title = _('Bereiche')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = _('Bereiche')

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        list_of_disciplines = []
        queryset = Discipline.objects.all()
        for discipline in queryset:
            list_of_disciplines.append(
                (str(discipline.id), discipline.title)
            )
        return sorted(list_of_disciplines, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(training_sets__discipline_id=self.value())
        return queryset


class DocumentTraininSetListFilter(admin.SimpleListFilter):
    """
    This filter will always return a subset of the instances in a Model, either filtering by the
    user choice or by a default value.
    """

    title = _('Module')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = _('Modul')

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        list_of_trainingsets = []
        queryset = TrainingSet.objects.all()
        for trainingset in queryset:
            list_of_trainingsets.append(
                (str(trainingset.id), trainingset.title)
            )
        return sorted(list_of_trainingsets, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(training_sets__id=self.value())
        return queryset


class DisciplineListFilter(admin.SimpleListFilter):
    """
    This filter will always return a subset of the instances in a Model, either filtering by the
    user choice or by a default value.
    """

    title = _('Bereiche')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = _('Bereich')

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        list_of_disciplines = []
        queryset = Discipline.objects.all()
        for discipline in queryset:
            list_of_disciplines.append(
                (str(discipline.id), discipline.title)
            )
        return sorted(list_of_disciplines, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(discipline_id=self.value())
        return queryset
