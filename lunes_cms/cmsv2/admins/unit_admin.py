from __future__ import absolute_import, annotations, unicode_literals

from datetime import date
from typing import Any, Iterable, TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.models.review import ReviewAssignment
from lunes_cms.cmsv2.models.unit import Unit, UnitWordRelation

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise


class WordInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing word relationships directly from the Unit admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
    extra = 1
    autocomplete_fields = ["word"]
    fields = [
        "word",
        "image_with_controls",
        "example_sentence",
        "example_sentence_generate",
        "example_sentence_check_status",
        "example_sentence_audio_player",
    ]
    readonly_fields = [
        "image_with_controls",
        "example_sentence_generate",
        "example_sentence_audio_player",
    ]


class ReviewAssignmentInline(admin.TabularInline):
    """
    Inline admin for ReviewAssignment.
    """

    model = ReviewAssignment
    fk_name = "unit"
    extra = 0
    fields = ["reviewer", "assigned_by", "assigned_at"]
    readonly_fields = ["assigned_by", "assigned_at"]
    autocomplete_fields = ["reviewer"]
    verbose_name = _("assigned user")
    verbose_name_plural = _("assigned users")

    def has_add_permission(self, request: HttpRequest, obj: Unit | None = None) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: Unit | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: Unit | None = None
    ) -> bool:
        return request.user.is_superuser


class MigratedFilter(admin.SimpleListFilter):
    """
    Admin filter for migration status.

    Allows filtering units by whether they were migrated from v1 or created in v2.
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

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Unit]
    ) -> QuerySet[Unit]:
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
        "migrated_status",
        "description",
        "icon",
        "image_tag",
        "jobs",
        "created_by",
        "released",
    ]
    readonly_fields = ["created_by", "image_tag", "migrated_status"]
    inlines = [WordInline, ReviewAssignmentInline]
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
    list_filter = ["released", MigratedFilter, "jobs"]
    list_per_page = 25
    actions = ["bulk_release", "assign_to_user"]

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the unit admin interface,
        particularly for asset management functionality.
        """

        js = [
            "js/cookies.js",
            "js/unit_icon_asset_config.js",
            "js/asset_manager.js",
            "js/generate_example_sentence.js",
        ]
        css = {"all": ["css/asset_manager.css"]}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Unit]:
        return super().get_queryset(request).prefetch_related("jobs")

    def save_formset(
        self,
        request: HttpRequest,
        form: ModelForm[Any],
        formset: BaseModelFormSet,
        change: bool,
    ) -> None:
        if formset.model is ReviewAssignment:
            instances = formset.save(commit=False)
            for obj in formset.deleted_objects:
                obj.delete()
            for instance in instances:
                if instance.assigned_by_id is None:
                    instance.assigned_by = request.user
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

    @admin.action(description=_("Release all selected units"))
    def bulk_release(self, request: HttpRequest, queryset: QuerySet[Unit]) -> None:
        """
        Bulk action to release selected units in one go
        """
        if not request.user.has_perm("change_unit"):
            raise PermissionDenied

        units_skipped = queryset.filter(released=True).count()
        released_unit_count = queryset.filter(released=False).update(released=True)

        self.message_user(
            request,
            _(
                "Released %(unit_count)d unit(s). %(units_skipped)d unit(s) were skipped, because they were already released"
            )
            % {
                "unit_count": released_unit_count,
                "units_skipped": units_skipped,
            },
        )

    @admin.action(description=_("Assign selected units to user"))
    def assign_to_user(
        self, request: HttpRequest, queryset: QuerySet[Unit]
    ) -> HttpResponse | None:
        """
        Bulk-create ReviewAssignments linking each selected unit to a chosen
        user. Superusers only. Units already assigned to the target user are
        silently skipped via the (unit, reviewer) unique constraint.
        """
        if not request.user.is_superuser:
            raise PermissionDenied

        if "apply" not in request.POST:
            return TemplateResponse(
                request,
                "admin/cmsv2/assign_units_to_user.html",
                {
                    **self.admin_site.each_context(request),
                    "units": queryset,
                    "users": User.objects.order_by("username"),
                    "action": "assign_to_user",
                    "selected_action": queryset.values_list("pk", flat=True),
                    "title": _("Assign selected units to user"),
                },
            )

        user = User.objects.get(pk=request.POST["user"])
        existing_unit_ids = set(
            ReviewAssignment.objects.filter(
                reviewer=user, unit__in=queryset
            ).values_list("unit_id", flat=True)
        )
        to_create = [
            ReviewAssignment(unit=unit, reviewer=user, assigned_by=request.user)
            for unit in queryset
            if unit.pk not in existing_unit_ids
        ]
        ReviewAssignment.objects.bulk_create(to_create, ignore_conflicts=True)
        self.message_user(
            request,
            _("Assigned %(new)d unit(s) to %(user)s (%(skipped)d already assigned).")
            % {
                "new": len(to_create),
                "skipped": len(existing_unit_ids),
                "user": user,
            },
        )
        return None

    def related_jobs(self, obj: Unit) -> str:
        """
        Get a comma-separated list of job names related to this unit.

        Args:
            obj: The unit object

        Returns:
            str: A comma-separated list of job names
        """
        return ", ".join([job.name for job in obj.jobs.all()])

    related_jobs.short_description = _("jobs")  # type: ignore[attr-defined]

    def creator_group(self, obj: Unit) -> str | Group | None:
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

    creator_group.short_description = _("creator group")  # type: ignore[attr-defined]

    def created_at_date(self, obj: Unit) -> date:
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The unit object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")  # type: ignore[attr-defined]

    def migrated_status(self, obj: Unit) -> SafeString:
        """
        Display a badge indicating whether the unit was migrated from v1 or created in v2.

        Args:
            obj: The unit object

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
