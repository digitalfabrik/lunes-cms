from __future__ import absolute_import, annotations, unicode_literals

from datetime import date
from typing import Any, Iterable, TYPE_CHECKING

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.forms import ModelForm
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.area_filters import JobListFilter
from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.areas import (
    area_of_unit,
    scope_jobs,
    scope_units,
    validate_relation_area,
    validate_unit_jobs,
)
from lunes_cms.cmsv2.models import Job
from lunes_cms.cmsv2.models.area import Area
from lunes_cms.cmsv2.models.review import Review
from lunes_cms.cmsv2.models.unit import Unit, UnitWordRelation
from lunes_cms.cmsv2.models.word import Word

if TYPE_CHECKING:
    from django.db.models import ManyToManyField
    from django.utils.functional import _StrOrPromise


class UnitAdminForm(ModelForm):
    """
    Form for the Unit model that keeps a unit inside a single area.
    """

    class Meta:
        """
        Meta class of the unit form
        """

        model = Unit
        fields = "__all__"

    def clean_jobs(self) -> QuerySet[Job]:
        """
        Reject job assignments that would mix areas.

        A unit of a job that belongs to an area must not be assigned to any
        other job, and it must not carry words that are already used elsewhere.
        """
        jobs = self.cleaned_data["jobs"]
        validate_unit_jobs(self.instance, jobs)
        return jobs


class WordInlineFormSet(BaseInlineFormSet):
    """
    Formset that keeps the words of a unit inside a single area.

    The words of a unit have to belong to the area of that unit, so a word of
    the main app cannot be added to a unit of an area and vice versa. New rows
    have no unit yet while they are validated, which is why the check cannot be
    left to ``UnitWordRelation.clean()`` alone.
    """

    def clean(self) -> None:
        super().clean()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            word = form.cleaned_data.get("word")
            if word:
                validate_relation_area(self.instance, word)


class WordInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing word relationships directly from the Unit admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
    formset = WordInlineFormSet
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

    form = UnitAdminForm
    fields = [
        "title",
        "migrated_status",
        "description",
        "icon",
        "image_tag",
        "jobs",
        "created_by",
        "created_by_user",
        "released",
    ]
    readonly_fields = ["created_by", "created_by_user", "image_tag", "migrated_status"]
    inlines = [WordInline]
    search_fields = ["title"]
    list_display = [
        "title",
        "migrated_status",
        "released",
        "list_icon",
        "related_jobs",
        "area",
        "creator_group",
        "created_by_user",
        "created_at_date",
    ]
    list_display_links = ["title"]
    list_filter = ["released", MigratedFilter, ("jobs", JobListFilter)]
    list_select_related = ["created_by", "created_by_user"]
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
        """Restrict the units to the area of the user and prefetch their jobs"""
        return scope_units(
            super().get_queryset(request).prefetch_related("jobs__area"), request.user
        )

    def formfield_for_manytomany(
        self,
        db_field: "ManyToManyField[Any, Any]",
        request: HttpRequest,
        **kwargs: Any,
    ) -> Any:
        """Offer only the jobs the user may see, so no unit escapes its area."""
        if db_field.name == "jobs":
            kwargs["queryset"] = scope_jobs(Job.objects.all(), request.user).order_by(
                "name"
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def area(self, obj: Unit) -> Area | None:
        """
        The area of the unit, derived from its job.

        Args:
            obj: The unit object

        Returns:
            Area or None: The area of the unit, or None for main app content
        """
        return area_of_unit(obj)

    area.short_description = _("area")  # type: ignore[attr-defined]

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
        Bulk-create Reviews linking every word of each selected unit to a
        chosen user. Superusers only. Words already assigned to the target
        user are silently skipped via the (word, reviewer) unique constraint.
        """
        if not request.user.is_authenticated or not request.user.is_superuser:
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
        words = Word.objects.filter(units__in=queryset).distinct()
        word_ids_assigned_to_user = set(
            Review.objects.filter(reviewer=user, word__in=words).values_list(
                "word_id", flat=True
            )
        )
        to_create = [
            Review(word=word, reviewer=user, assigned_by=request.user)
            for word in words
            if word.pk not in word_ids_assigned_to_user
        ]
        Review.objects.bulk_create(to_create, ignore_conflicts=True)
        self.message_user(
            request,
            _("Assigned %(new)d word(s) to %(user)s (%(skipped)d already assigned).")
            % {
                "new": len(to_create),
                "skipped": len(word_ids_assigned_to_user),
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

    creator_group.short_description = _("group")  # type: ignore[attr-defined]

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
