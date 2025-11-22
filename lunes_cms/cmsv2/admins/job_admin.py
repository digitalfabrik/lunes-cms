from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .base import BaseAdmin
from ..models import Unit


class UnitInline(admin.TabularInline):
    """
    Inline admin for the relationship between Job and Unit models.

    This inline allows adding and editing units directly from the Job admin page.
    """

    model = Unit.jobs.through
    extra = 1


class MigratedFilter(admin.SimpleListFilter):
    """
    Admin filter for migration status.

    Allows filtering jobs by whether they were migrated from v1 or created in v2.
    """

    title = _("migration status")
    parameter_name = "migrated"

    def lookups(self, request, model_admin):
        """
        Return the filter options.

        Returns:
            list: A list of tuples containing (value, label) pairs for the filter options
        """
        return [
            ("yes", _("Migrated from old data model")),
            ("no", _("Not migrated from old data model")),
        ]

    def queryset(self, request, queryset):
        """
        Filter the queryset based on the selected option.

        Args:
            request: The HTTP request
            queryset: The queryset to filter

        Returns:
            QuerySet: The filtered queryset
        """
        if self.value() == "yes":
            return queryset.filter(v1_id__isnull=False)
        if self.value() == "no":
            return queryset.filter(v1_id__isnull=True)
        return queryset


class JobAdmin(BaseAdmin):
    """
    Admin interface for the Job model.

    This admin class provides a comprehensive interface for managing jobs,
    including their attributes, icons, and relationships with units.
    """

    fields = [
        "name",
        "migrated_status",
        "icon",
        "image_tag",
        "created_by",
        "released",
    ]
    readonly_fields = ["created_by", "image_tag", "migrated_status"]
    inlines = [UnitInline]
    search_fields = ["name"]
    list_display = [
        "name",
        "migrated_status",
        "released",
        "list_icon",
        "created_by",
        "created_at_date",
    ]
    list_display_links = ["name"]
    list_filter = ["released", MigratedFilter]
    list_per_page = 25
    ordering = ["name"]

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the job admin interface,
        particularly for asset management functionality.
        """

        js = ["js/job_icon_asset_config.js", "js/asset_manager.js"]
        css = {"all": ["css/asset_manager.css"]}

    def related_units(self, obj):
        """
        Get a comma-separated list of unit titles related to this job.

        Args:
            obj: The job object

        Returns:
            str: A comma-separated list of unit titles
        """
        return ", ".join([unit.title for unit in obj.units.all()])

    related_units.short_description = _("units")

    def created_at_date(self, obj):
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The job object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")

    def migrated_status(self, obj):
        """
        Display a badge indicating whether the job was migrated from v1 or created in v2.

        Args:
            obj: The job object

        Returns:
            str: HTML formatted badge showing migration status
        """
        if obj.v1_id is not None:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 13px; font-weight: 500;">Migrated</span>'
            )
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 13px; font-weight: 500;">New</span>'
        )

    migrated_status.short_description = _("migrated")
