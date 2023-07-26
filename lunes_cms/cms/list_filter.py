from collections import defaultdict

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

    template = "admin/discipline_filter.html"

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

        # Verify that only disciplines are displayed that actually can contain training sets
        queryset = Discipline.objects.filter(lft=F("rght") - 1)

        if "training set" in request.GET:
            queryset = queryset.filter(training_sets=request.GET["training set"])

        if request.user.is_superuser:
            queryset = queryset.filter(creator_is_admin=True)
        else:
            queryset = queryset.filter(created_by__in=request.user.groups.all())

        list_of_disciplines = [
            (
                str(discipline.id),
                f"{discipline.parent} \u2794 {discipline}",
            )
            for discipline in queryset
        ]
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
            return queryset.filter(discipline=self.value()).distinct()
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
            return queryset.filter(training_sets__discipline=self.value()).distinct()
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
        queryset = TrainingSet.objects.all()
        if "disciplines" in request.GET:
            queryset = queryset.filter(discipline=request.GET["disciplines"])
        if request.user.is_superuser:
            queryset = queryset.filter(creator_is_admin=True)
        else:
            queryset = queryset.filter(created_by__in=request.user.groups.all())
        list_of_trainingsets = [
            ((str(trainingset.id), trainingset.title)) for trainingset in queryset
        ]
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


NONE = "none"
PENDING = "pending"
APPROVED = "approved"
NO_APPROVED = "no-approved"


class ApprovedImageListFilter(admin.SimpleListFilter):
    """
    Filter for approved images within document list display.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("Images")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "images"

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
            (APPROVED, _("At least one approved image")),
            (PENDING, _("At least one pending image")),
            (NO_APPROVED, _("No approved images")),
            (NONE, _("No images")),
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
            if self.value() == NONE:
                return queryset.filter(document_image__isnull=True).distinct()
            elif self.value() == PENDING:
                return queryset.filter(document_image__confirmed=False).distinct()
            elif self.value() == APPROVED:
                return queryset.filter(document_image__confirmed=True).distinct()
            elif self.value() == NO_APPROVED:
                return queryset.exclude(document_image__confirmed=True).distinct()
        return queryset


NONE = "none"
AT_LEAST_ONE = "at-least-one"
RELEASED = "released"
RELEASED_DISCIPLINE = "released-discipline"
UNRELEASED = "unreleased"


class AssignedListFilter(admin.SimpleListFilter):
    """
    Filter for documents that are either assigned or unassigned to at least one training set.
    Inherits from `admin.SimpleListFilter`.
    """

    title = _("Assignments")

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
            (NONE, _("Not assigned to any module")),
            (AT_LEAST_ONE, _("Assigned to at least one module")),
            (RELEASED, _("Assigned to released modules")),
            (
                RELEASED_DISCIPLINE,
                _("Assigned to released modules in released disciplines"),
            ),
            (UNRELEASED, _("Assigned to unreleased modules")),
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

        filters = {}
        if self.value():
            if "disciplines" in request.GET:
                filters["training_sets__discipline"] = request.GET["disciplines"]
            if "training set" in request.GET:
                filters["training_sets"] = request.GET["training set"]
            if self.value() == NONE:
                filters["training_sets__isnull"] = True
            elif self.value() == AT_LEAST_ONE:
                filters["training_sets__isnull"] = False
            elif self.value() == RELEASED:
                filters["training_sets__released"] = True
            elif self.value() == RELEASED_DISCIPLINE:
                filters["training_sets__released"] = True
                filters["training_sets__discipline__released"] = True
            elif self.value() == UNRELEASED:
                filters["training_sets__released"] = False
        return queryset.filter(**filters).distinct()
