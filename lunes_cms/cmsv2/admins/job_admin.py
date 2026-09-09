from __future__ import absolute_import, annotations, unicode_literals

import io
from datetime import date
from typing import Any, Iterable, Iterator, TYPE_CHECKING
from zipfile import ZipFile

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _
from tablib import Dataset

from ..areas import administered_areas, scope_jobs, validate_unit_jobs
from ..models import Job, Unit, Word
from ..utils import make_safe_filename
from .area_filters import AreaListFilter
from .base import BaseAdmin
from .word_export_resource import WordExportResource

if TYPE_CHECKING:
    from django.contrib.admin.filters import _ListFilterChoices
    from django.contrib.admin.views.main import ChangeList
    from django.db.models import ForeignKey, Model
    from django.forms import ModelChoiceField, ModelForm
    from django.utils.functional import _StrOrPromise


class UnitJobInlineFormSet(BaseInlineFormSet):
    """
    Formset that keeps the units of a job inside a single area.

    A unit of a job that belongs to an area must not be assigned to any other
    job, so adding an already used unit to such a job has to be rejected here —
    the constraint spans the many-to-many relation and can neither be expressed
    in the database nor checked in ``Unit.clean()``.
    """

    def clean(self) -> None:
        super().clean()
        job = self.instance
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            unit = form.cleaned_data.get("unit")
            if not unit:
                continue
            other_jobs = (
                list(unit.jobs.exclude(pk=job.pk)) if job.pk else list(unit.jobs.all())
            )
            validate_unit_jobs(unit, [job, *other_jobs])


class UnitInline(admin.TabularInline):
    """
    Inline admin for the relationship between Job and Unit models.

    This inline allows adding and editing units directly from the Job admin page.
    """

    model = Unit.jobs.through
    formset = UnitJobInlineFormSet
    extra = 1
    autocomplete_fields = ["unit"]


class MigratedFilter(admin.SimpleListFilter):
    """
    Admin filter for migration status.

    Allows filtering jobs by whether they were migrated from v1 or created in v2.
    """

    title = _("migration status")
    parameter_name = "migrated"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[tuple[str, "_StrOrPromise"]]:
        """
        Return the filter options.

        Returns:
            list: A list of tuples containing (value, label) pairs for the filter options
        """
        return [
            ("yes", _("Migrated from old data model")),
            ("no", _("Not migrated from old data model")),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Job]) -> QuerySet[Job]:
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


class ArchivedFilter(admin.SimpleListFilter):
    """
    Admin filter for the archive status of jobs.

    By default only active (non-archived) jobs are shown. The filter allows
    content managers to view archived jobs or all jobs.
    """

    title = _("archive status")
    parameter_name = "archived"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin
    ) -> Iterable[tuple[str, "_StrOrPromise"]]:
        """
        Return the additional filter options.

        Returns:
            list: A list of tuples containing (value, label) pairs for the filter options
        """
        return [
            ("archived", _("Archived jobs")),
            ("all", _("All jobs")),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Job]) -> QuerySet[Job]:
        """
        Filter the queryset based on the selected option.

        Defaults to showing only active jobs when no option is selected.

        Args:
            request: The HTTP request
            queryset: The queryset to filter

        Returns:
            QuerySet: The filtered queryset
        """
        if self.value() == "archived":
            return queryset.filter(archived=True)
        if self.value() == "all":
            return queryset
        return queryset.filter(archived=False)

    def choices(self, changelist: "ChangeList") -> Iterator["_ListFilterChoices"]:
        """
        Yield the filter choices, using "Active jobs" as the default selection.
        """
        yield {
            "selected": self.value() is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": _("Active jobs"),
        }
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == str(lookup),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup}
                ),
                "display": title,
            }


class JobAdmin(BaseAdmin):
    """
    Admin interface for the Job model.

    This admin class provides a comprehensive interface for managing jobs,
    including their attributes, icons, and relationships with units.
    """

    fields = [
        "name",
        "area",
        "migrated_status",
        "icon",
        "image_tag",
        "created_by",
        "created_by_user",
        "released",
        "archived",
        "import_csv_link",
    ]
    readonly_fields = [
        "created_by",
        "created_by_user",
        "image_tag",
        "migrated_status",
        "import_csv_link",
    ]
    inlines = [UnitInline]
    search_fields = ["name"]
    list_display = [
        "name",
        "area",
        "migrated_status",
        "released",
        "archived",
        "list_icon",
        "created_by",
        "created_by_user",
        "created_at_date",
    ]
    list_display_links = ["name"]
    list_filter = [ArchivedFilter, "released", MigratedFilter, ("area", AreaListFilter)]
    list_select_related = ["area", "created_by", "created_by_user"]
    actions = ["export_to_csv", "duplicate_jobs", "archive_jobs", "restore_jobs"]
    list_per_page = 25
    ordering = ["name"]
    change_list_template = "admin/cmsv2/import_csv_button.html"
    change_form_template = "admin/cmsv2/save_and_import_button.html"

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the job admin interface,
        particularly for asset management functionality.
        """

        js = ["js/cookies.js", "js/job_icon_asset_config.js", "js/asset_manager.js"]
        css = {"all": ["css/asset_manager.css"]}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Job]:
        """Restrict the jobs to the area of the user and prefetch their units"""
        return scope_jobs(
            super().get_queryset(request).prefetch_related("units"), request.user
        )

    def get_readonly_fields(
        self, request: HttpRequest, obj: Job | None = None
    ) -> list[str]:
        """
        Only superusers may move a job between areas.

        An area administrator who administers several areas still has to pick
        one when creating a job, so the field stays editable on the add form —
        limited to their own areas, see :meth:`formfield_for_foreignkey`.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if request.user.is_superuser:
            return readonly_fields
        if obj is None and len(administered_areas(request.user)) > 1:
            return readonly_fields
        return [*readonly_fields, "area"]

    def formfield_for_foreignkey(
        self,
        db_field: "ForeignKey[Any, Any]",
        request: HttpRequest,
        **kwargs: Any,
    ) -> "ModelChoiceField[Any] | None":
        """Offer an area administrator only the areas they administer."""
        if db_field.name == "area" and not request.user.is_superuser:
            kwargs["queryset"] = administered_areas(request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(
        self,
        request: HttpRequest,
        obj: Job,
        form: "ModelForm[Model]",
        change: bool,
    ) -> None:
        """
        Put a job an area administrator creates into their area.

        Administrators of a single area never see the field, so it is filled in
        for them here, the same way ``created_by`` is.
        """
        if not change and not request.user.is_superuser and obj.area is None:
            areas = administered_areas(request.user)
            if len(areas) == 1:
                obj.area = areas[0]
        super().save_model(request, obj, form, change)

    def related_units(self, obj: Job) -> str:
        """
        Get a comma-separated list of unit titles related to this job.

        Args:
            obj: The job object

        Returns:
            str: A comma-separated list of unit titles
        """
        return ", ".join([unit.title for unit in obj.units.all()])

    related_units.short_description = _("units")  # type: ignore[attr-defined]

    def created_at_date(self, obj: Job) -> date:
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The job object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")  # type: ignore[attr-defined]

    def migrated_status(self, obj: Job) -> SafeString:
        """
        Display a badge indicating whether the job was migrated from v1 or created in v2.

        Args:
            obj: The job object

        Returns:
            str: HTML formatted badge showing migration status
        """
        if obj.v1_id is not None:
            return mark_safe(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 13px; font-weight: 500;">Migrated</span>'
            )
        return mark_safe(
            '<span style="background-color: #007bff; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 13px; font-weight: 500;">New</span>'
        )

    migrated_status.short_description = _("migrated")  # type: ignore[attr-defined]

    @admin.action(description=_("Export all vocabulary for these jobs to CSV"))
    def export_to_csv(self, _: HttpRequest, queryset: QuerySet[Job]) -> HttpResponse:
        """
        Export the words of the selected jobs.

        :param request: current user request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        csvs = {}

        for profession in queryset:
            resource = WordExportResource(for_profession=profession)
            units = Unit.objects.filter(jobs=profession)
            words = (
                Word.objects.filter(units__in=units)
                .order_by("units__title", "word")
                .distinct()
            )

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

    @admin.action(description=_("Duplicate selected jobs"))
    def duplicate_jobs(self, request: HttpRequest, queryset: QuerySet[Job]) -> None:
        """
        Duplicate the selected jobs, including their related units.

        Jobs of an area are skipped: their units must not be shared with a
        second job, so duplicating them would need a deep copy of every unit
        and word, which is a separate feature.
        """
        skipped = queryset.filter(area__isnull=False).count()
        if skipped:
            messages.warning(
                request,
                _(
                    "%(count)d job(s) were skipped, because jobs of an area "
                    "cannot be duplicated."
                )
                % {"count": skipped},
            )
        for job in queryset.filter(area__isnull=True):
            units = list(job.units.all())
            job.pk = None
            job.v1_id = None
            job.released = False
            job.archived = False
            new_label = _("New")
            job.name = f"{job.name} ({new_label})"
            job.created_by = request.user.groups.first()
            # request.user is `User | AnonymousUser`, but this action is only
            # reachable by authenticated staff users.
            job.created_by_user = request.user  # type: ignore[assignment]
            job.save()
            job.units.set(units)
        messages.success(request, _("Selected jobs have been duplicated successfully."))

    @admin.action(description=_("Archive selected jobs"))
    def archive_jobs(self, request: HttpRequest, queryset: QuerySet[Job]) -> None:
        """Archive the selected jobs so they are no longer published or listed."""
        updated = queryset.update(archived=True, released=False)
        messages.success(
            request,
            _("%(count)d job(s) have been archived successfully.") % {"count": updated},
        )

    @admin.action(description=_("Restore selected jobs from archive"))
    def restore_jobs(self, request: HttpRequest, queryset: QuerySet[Job]) -> None:
        """Restore the selected jobs from the archive."""
        updated = queryset.update(archived=False)
        messages.success(
            request,
            _("%(count)d job(s) have been restored successfully.") % {"count": updated},
        )

    def response_add(
        self,
        request: HttpRequest,
        obj: Job,
        post_url_continue: str | None = None,
    ) -> HttpResponse:
        if "_save_and_import" in request.POST:
            return redirect(reverse("cmsv2:import_csv_for_job", args=[obj.pk]))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request: HttpRequest, obj: Job) -> HttpResponse:
        if "_save_and_import" in request.POST:
            return redirect(reverse("cmsv2:import_csv_for_job", args=[obj.pk]))
        return super().response_change(request, obj)

    def import_csv_link(self, obj: Job) -> str:
        """
        Add link/button for importing csv files from job list view
        """
        if obj.pk:
            url = reverse("cmsv2:import_csv_for_job", args=[obj.pk])
            return format_html('<a class="button" href="{}">Import CSV</a>', url)
        return "—"

    import_csv_link.short_description = _("Import")  # type: ignore[attr-defined]
