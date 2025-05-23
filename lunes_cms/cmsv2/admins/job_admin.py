from __future__ import absolute_import, unicode_literals

from django.contrib import admin
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


class JobAdmin(BaseAdmin):
    """
    Admin interface for the Job model.

    This admin class provides a comprehensive interface for managing jobs,
    including their attributes, icons, and relationships with units.
    """

    fields = [
        "name",
        "icon",
        "image_tag",
        "created_by",
        "released",
    ]
    readonly_fields = ["created_by", "image_tag"]
    inlines = [UnitInline]
    search_fields = ["name"]
    list_display = [
        "name",
        "released",
        "list_icon",
        "created_by",
        "created_at_date",
    ]
    list_display_links = ["name"]
    list_filter = ["released"]
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
