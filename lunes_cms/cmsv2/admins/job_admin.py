from __future__ import absolute_import, unicode_literals

import io
from zipfile import ZipFile

from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..models import Unit, Word
from ..utils import make_safe_filename
from .base import BaseAdmin
from .word_export_resource import WordExportResource


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
        "import_csv_link",
    ]
    readonly_fields = ["created_by", "image_tag", "migrated_status", "import_csv_link"]
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
    actions = ["export_to_csv"]
    list_per_page = 25
    ordering = ["name"]
    change_list_template = "admin/cmsv2/job_change_list.html"
    change_form_template = "admin/cmsv2/job_change_form.html"

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

    related_units.short_description = _("units")  # type: ignore[attr-defined]

    def created_at_date(self, obj):
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The job object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")  # type: ignore[attr-defined]

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

    migrated_status.short_description = _("migrated")  # type: ignore[attr-defined]

    @admin.action(description=_("Export all vocabulary for these jobs to CSV"))
    def export_to_csv(self, request, queryset):
        """
        Export the words of the selected disciplines.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        csvs = {}

        for profession in queryset:
            resource = WordExportResource()
            units = Unit.objects.filter(jobs=profession)
            words = Word.objects.filter(units__in=units).distinct()

            dataset = Dataset(
                *(resource.export_resource(word) for word in words),
                headers=resource.export().headers,
            )

            csvs[profession] = dataset.csv

        zip_buffer = io.BytesIO()

        with ZipFile(zip_buffer, "w") as zipfile:
            for profession, csv in csvs.items():
                zipfile.writestr(f"{make_safe_filename(profession.name)}.csv", csv)

        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="Lunes_vocabulary.zip"'
        return response

    def response_add(self, request, obj, post_url_continue=None):
        if "_save_and_import" in request.POST:
            return redirect(reverse("cmsv2:import_csv_for_job", args=[obj.pk]))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "_save_and_import" in request.POST:
            return redirect(reverse("cmsv2:import_csv_for_job", args=[obj.pk]))
        return super().response_change(request, obj)

    def import_csv_link(self, obj) -> str:
        """
        Add link/button for importing csv files from job list view
        """
        if obj.pk:
            url = reverse("cmsv2:import_csv_for_job", args=[obj.pk])
            return format_html('<a class="button" href="{}">Import CSV</a>', url)
        return "—"

    import_csv_link.short_description = _("Import")  # type: ignore[attr-defined]
