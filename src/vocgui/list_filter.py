from __future__ import absolute_import, unicode_literals
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Discipline, DocumentImage, TrainingSet, Document


class DocumentDisciplineListFilter(admin.SimpleListFilter):
    """
    This filter will return a subset of the instances in a Model by filtering according to the
    user choice.
    """

    title = _("disciplines")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "disciplines"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.

        :param self: A handle to the :class:`list_filter.DocumentDisciplineListFilter`
        :type self: class: `list_filter.DocumentDisciplineListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin

        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        list_of_disciplines = []
        queryset = Discipline.objects.all()
        for discipline in queryset:
            list_of_disciplines.append((str(discipline.id), discipline.title))
        return sorted(list_of_disciplines, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param self: A handle to the :class:`list_filter.DocumentDisciplineListFilter`
        :type self: class: `list_filter.DocumentDisciplineListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param queryset: current queryset
        :type queryset: QuerySet

        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(
                training_sets__discipline__id=self.value()
            ).distinct()
        return queryset


class DocumentTrainingSetListFilter(admin.SimpleListFilter):
    """
    This filter will return a subset of the instances in a Model by filtering according to the
    user choice.
    """

    title = _("training sets")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "training set"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.

        :param self: A handle to the :class:`list_filter.DocumentTrainingSetListFilter`
        :type self: class: `list_filter.DocumentTrainingSetListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin

        :return: list of tuples containing id and title of each training set
        :rtype: list
        """
        list_of_trainingsets = []
        queryset = TrainingSet.objects.all()
        for trainingset in queryset:
            list_of_trainingsets.append((str(trainingset.id), trainingset.title))
        return sorted(list_of_trainingsets, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param self: A handle to the :class:`list_filter.DocumentTrainingSetListFilter`
        :type self: class: `list_filter.DocumentTrainingSetListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param queryset: current queryset
        :type queryset: QuerySet

        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(training_sets__id=self.value()).distinct()
        return queryset


class DisciplineListFilter(admin.SimpleListFilter):
    """This filter will return a subset of the instances in a Model by filtering according to the
    user choice.
    """

    title = _("disciplines")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "discipline"

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.

        :param self: A handle to the :class:`list_filter.DisciplineListFilter`
        :type self: class: `list_filter.DisciplineListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin

        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        list_of_disciplines = []
        queryset = Discipline.objects.all()
        for discipline in queryset:
            list_of_disciplines.append((str(discipline.id), discipline.title))
        return sorted(list_of_disciplines, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param self: A handle to the :class:`list_filter.DisciplineListFilter`
        :type self: class: `list_filter.DisciplineListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param queryset: current queryset
        :type queryset: QuerySet

        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        # Compare the requested value to decide how to filter the queryset.
        if self.value():
            return queryset.filter(discipline__id=self.value()).distinct()
        return queryset


class ApprovedImageListFilter(admin.SimpleListFilter):
    """This filter will return a subset of the instances in a Model by filtering according to the
    user choice.
    """

    title = _("approved images")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "approvedimages"

    default_value = None

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.

        :param self: A handle to the :class:`list_filter.ApprovedImageListFilter`
        :type self: class: `list_filter.ApprovedImageListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin

        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        return (
            (1, _("approved")),
            (2, _("pending")),
            (3, _("no images")),
        )


    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param self: A handle to the :class:`list_filter.DisciplineListFilter`
        :type self: class: `list_filter.DisciplineListFilter`
        :param request: Current HTTP request
        :type request: HTTP request
        :param queryset: current queryset
        :type queryset: QuerySet

        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """

        # Compare the requested value to decide how to filter the queryset.
        #DocumentImage.objects.all().filter(document = obj)
        return None