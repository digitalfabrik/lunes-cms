from django.contrib import admin
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from ...models import Discipline


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
