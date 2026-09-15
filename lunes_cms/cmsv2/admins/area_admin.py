from __future__ import absolute_import, annotations, unicode_literals

from datetime import date

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..models import Area, AreaCode


class AreaCodeInline(admin.TabularInline):
    """
    Inline admin for the codes of an area.

    The codes are edited together with their area, because they only make sense
    as part of it and are managed by the same people.
    """

    model = AreaCode
    extra = 1
    fields = ["code", "created_at"]
    readonly_fields = ["created_at"]
    verbose_name = _("code")
    verbose_name_plural = _("codes")


class AreaAdmin(admin.ModelAdmin):
    """
    Admin interface for the Area model.

    Areas are created and assigned by superusers only, because assigning an
    area decides who may see and change the content below it.
    """

    fields = ["name", "admins"]
    filter_horizontal = ["admins"]
    inlines = [AreaCodeInline]
    search_fields = ["name"]
    ordering = ["name"]
    list_display = [
        "name",
        "administrators",
        "number_jobs",
        "number_codes",
        "created_at_date",
    ]
    list_display_links = ["name"]
    list_per_page = 25

    def get_queryset(self, request: HttpRequest) -> QuerySet[Area]:
        """Annotate the job and code counts and prefetch the administrators."""
        return (
            super()
            .get_queryset(request)
            .annotate(job_count=Count("jobs", distinct=True))
            .annotate(code_count=Count("codes", distinct=True))
            .prefetch_related("admins")
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def administrators(self, obj: Area) -> str:
        """
        Get a comma-separated list of the administrators of this area.

        Args:
            obj: The area object

        Returns:
            str: A comma-separated list of user names
        """
        return ", ".join(user.get_username() for user in obj.admins.all())

    administrators.short_description = _("administrators")  # type: ignore[attr-defined]

    def number_jobs(self, obj: Area) -> int:
        """
        Get the number of jobs that belong to this area.

        Args:
            obj: The area object

        Returns:
            int: The number of jobs of the area
        """
        return obj.job_count  # type: ignore[attr-defined]

    number_jobs.short_description = _("jobs")  # type: ignore[attr-defined]

    def number_codes(self, obj: Area) -> int:
        """
        Get the number of codes that belong to this area.

        Args:
            obj: The area object

        Returns:
            int: The number of codes of the area
        """
        return obj.code_count  # type: ignore[attr-defined]

    number_codes.short_description = _("codes")  # type: ignore[attr-defined]

    def created_at_date(self, obj: Area) -> date:
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The area object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")  # type: ignore[attr-defined]
