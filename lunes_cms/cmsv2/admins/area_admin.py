from __future__ import absolute_import, annotations, unicode_literals

from datetime import date

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..models import Area


class AreaAdmin(admin.ModelAdmin):
    """
    Admin interface for the Area model.

    Areas are created and assigned by superusers only, because assigning an
    area decides who may see and change the content below it.
    """

    fields = ["name", "admins"]
    filter_horizontal = ["admins"]
    search_fields = ["name"]
    ordering = ["name"]
    list_display = ["name", "administrators", "number_jobs", "created_at_date"]
    list_display_links = ["name"]
    list_per_page = 25

    def get_queryset(self, request: HttpRequest) -> QuerySet[Area]:
        """Annotate the job count and prefetch the administrators."""
        return (
            super()
            .get_queryset(request)
            .annotate(job_count=Count("jobs"))
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
