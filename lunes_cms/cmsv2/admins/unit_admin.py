from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.models.unit import UnitWordRelation


class WordInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing word relationships directly from the Unit admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
    extra = 1
    fields = [
        "word",
        "image_with_controls",
        "example_sentence",
        "example_sentence_check_status",
        "example_sentence_audio_player",
    ]
    readonly_fields = ["image_with_controls", "example_sentence_audio_player"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


class MigratedFilter(admin.SimpleListFilter):
    """
    Admin filter for migration status.

    Allows filtering units by whether they were migrated from v1 or created in v2.
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


class UnitAdmin(BaseAdmin):
    """
    Admin interface for the Unit model.

    This admin class provides a comprehensive interface for managing units,
    including their attributes, icons, and relationships with words and jobs.
    """

    fields = [
        "title",
        "description",
        "icon",
        "image_tag",
        "jobs",
        "created_by",
        "released",
    ]
    readonly_fields = ["created_by", "image_tag"]
    inlines = [WordInline]
    search_fields = ["title"]
    list_display = [
        "title",
        "migrated_status",
        "released",
        "list_icon",
        "related_jobs",
        "creator_group",
        "created_at_date",
    ]
    list_display_links = ["title"]
    list_filter = ["released", MigratedFilter]
    list_per_page = 25

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the unit admin interface,
        particularly for asset management functionality.
        """

        js = ["js/unit_icon_asset_config.js", "js/asset_manager.js"]
        css = {"all": ["css/asset_manager.css"]}

    def related_jobs(self, obj):
        """
        Get a comma-separated list of job names related to this unit.

        Args:
            obj: The unit object

        Returns:
            str: A comma-separated list of job names
        """
        return ", ".join([job.name for job in obj.jobs.all()])

    related_jobs.short_description = _("jobs")

    def creator_group(self, obj):
        """
        Determine the creator group for display in the admin interface.

        Args:
            obj: The unit object

        Returns:
            str or None: "Admin" if created by an admin, the group name if created by a group,
                         or None if no creator information is available
        """
        if obj.creator_is_admin:
            return "Admin"
        if obj.created_by:
            return obj.created_by
        return None

    creator_group.short_description = _("creator group")

    def created_at_date(self, obj):
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The unit object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")

    def migrated_status(self, obj):
        """
        Display a badge indicating whether the unit was migrated from v1 or created in v2.

        Args:
            obj: The unit object

        Returns:
            str: HTML formatted badge showing migration status
        """
        if obj.v1_id is not None:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: 500;">Migrated</span>'
            )
        return format_html(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: 500;">New</span>'
        )

    migrated_status.short_description = _("migrated")
