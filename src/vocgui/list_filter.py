from __future__ import absolute_import, unicode_literals
from django.contrib import admin
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from .models import Discipline, TrainingSet


class DisciplineListFilter(admin.SimpleListFilter):
    """
    Generic Filter for models that have a direct relationship to disciplines.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("disciplines")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "disciplines"

    def lookups(self, request, model_admin):
        """
        Defining look up values that can be seen in the admin
        interface. Returns tuples: the first element is a coded
        value, whereas the second one is human-readable.

        :param request: current user request
        :type request: django.http.request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin
        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        list_of_disciplines = []

        # Verify that only disciplines are displayed that actually can contain training sets
        queryset = Discipline.objects.filter(lft=F("rght") - 1)

        if request.user.is_superuser:
            queryset = queryset.filter(creator_is_admin=True)
        else:
            queryset = queryset.filter(created_by__in=request.user.groups.all())
        for discipline in queryset:
            list_of_disciplines.append(
                (
                    str(discipline.id),
                    " \u2794 ".join(
                        map(str, discipline.get_ancestors(include_self=True))
                    ),
                )
            )
        return sorted(list_of_disciplines, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        if self.value():
            return queryset.filter(discipline__id=self.value()).distinct()
        return queryset


class DocumentDisciplineListFilter(DisciplineListFilter):
    """
    Filter for disciplines within document list display.
    Inherits from `admin.SimpleListFilter`.
    """

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        if self.value():
            return queryset.filter(
                training_sets__discipline__id=self.value()
            ).distinct()
        return queryset


class DocumentTrainingSetListFilter(admin.SimpleListFilter):
    """
    Filter for training sets within document list display.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("training sets")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "training set"

    def lookups(self, request, model_admin):
        """
        Defining look up values that can be seen in the admin
        interface. Returns tuples: the first element is a coded
        value, whereas the second one is human-readable.

        :param request: current user request
        :type request: django.http.request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin
        :return: list of tuples containing id and title of each training set
        :rtype: list
        """
        list_of_trainingsets = []
        if request.user.is_superuser:
            queryset = TrainingSet.objects.all().filter(creator_is_admin=True)
        else:
            queryset = TrainingSet.objects.all().filter(
                created_by__in=request.user.groups.all()
            )
        for trainingset in queryset:
            list_of_trainingsets.append((str(trainingset.id), trainingset.title))
        return sorted(list_of_trainingsets, key=lambda tp: tp[1])

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """
        if self.value():
            return queryset.filter(training_sets__id=self.value()).distinct()
        return queryset


class ApprovedImageListFilter(admin.SimpleListFilter):
    """
    Filter for approved images within document list display.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("approved images")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "approvedimages"

    default_value = None

    def lookups(self, request, model_admin):
        """
        Defining look up values that can be seen in the admin
        interface. Returns tuples: the first element is a coded
        value, whereas the second one is human-readable

        :param request: current user request
        :type request: django.http.request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin
        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        return (
            (1, _("at least one approved image")),
            (2, _("at least one pending image")),
            (3, _("no images")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """

        if self.value():
            if int(self.value()) == 1:
                return queryset.filter(document_image__confirmed=True).distinct()
            if int(self.value()) == 2:
                return queryset.filter(document_image__confirmed=False).distinct()
            if int(self.value()) == 3:
                return queryset.filter(document_image__isnull=True).distinct()
        return queryset


class AssignedListFilter(admin.SimpleListFilter):
    """
    Filter for documents that are either assigned or unassigned to at least one training set.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("assigned & unassigned")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "assigned"

    default_value = None

    def lookups(self, request, model_admin):
        """
        Defining look up values that can be seen in the admin
        interface. Returns tuples: the first element is a coded
        value, whereas the second one is human-readable

        :param request: current user request
        :type request: django.http.request
        :param model_admin: admin of current model
        :type model_admin: ModelAdmin
        :return: list of tuples containing id and title of each discipline
        :rtype: list
        """
        return (
            (0, _("unassigned only")),
            (1, _("assigned only")),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        :return: filtered queryset based on the value provided in the query string
        :rtype: QuerySet
        """

        if self.value():
            if int(self.value()) == 0:
                return queryset.filter(training_sets__isnull=True).distinct()
            if int(self.value()) == 1:
                return queryset.filter(training_sets__isnull=False).distinct()
        return queryset
