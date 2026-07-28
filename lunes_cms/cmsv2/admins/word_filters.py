from __future__ import absolute_import, annotations, unicode_literals

from typing import Iterable, TYPE_CHECKING

from django.contrib import admin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.unit import Unit

if TYPE_CHECKING:
    # `_StrOrPromise` only exists in django-stubs, not at runtime.
    from django.utils.functional import _StrOrPromise


class HasImageFilter(admin.SimpleListFilter):
    """Filter for displaying words with or without images."""

    title = _("Has Image")
    parameter_name = "has_image"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        return [
            ("yes", _("Yes")),
            ("no", _("No")),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        if self.value() == "yes":
            return queryset.exclude(image="")
        if self.value() == "no":
            return queryset.filter(image="")
        return queryset


class UnitOrJobDropdownFilter(admin.SimpleListFilter):
    """Filter for displaying units or jobs in the admin interface."""

    title = _("Unit or Job")
    parameter_name = "unit_or_job_choice"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        options = []
        for unit in Unit.objects.all():
            options.append((f"unit_{unit.pk}", f"Unit: {unit.title}"))
        for job in Job.objects.all():
            options.append((f"job_{job.pk}", f"Job: {job.name}"))
        return options

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        value = self.value()
        if not value:
            return queryset

        if value.startswith("unit_"):
            unit_id = value.split("_", 1)[1]
            return queryset.filter(units__id=unit_id).distinct()

        if value.startswith("job_"):
            job_id = value.split("_", 1)[1]
            return queryset.filter(units__jobs__id=job_id).distinct()

        return queryset


class HasCompleteExampleSentenceFilter(admin.SimpleListFilter):
    """Filter for displaying words that have a complete example sentence package."""

    title = _("Has Complete Example Sentence")
    parameter_name = "has_complete_example_sentence"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        return [
            ("yes", _("Yes")),
            ("no", _("No")),
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        if self.value() == "yes":
            # Filter words that HAVE a complete example sentence package
            # (check status is CONFIRMED AND sentence audio file exists)
            return (
                queryset.filter(
                    example_sentence__isnull=False,
                    example_sentence_check_status="CONFIRMED",
                )
                .exclude(
                    Q(example_sentence="")
                    | Q(example_sentence_audio="")
                    | Q(example_sentence_audio__isnull=True)
                )
                .distinct()
            )
        if self.value() == "no":
            # Filter words that DO NOT have a complete example sentence package
            # (no example sentence at all OR check status is NOT CONFIRMED OR sentence audio file is missing)
            return queryset.filter(
                Q(example_sentence__isnull=True)
                | Q(example_sentence="")
                | ~Q(example_sentence_check_status="CONFIRMED")
                | Q(example_sentence_audio="")
                | Q(example_sentence_audio__isnull=True)
            ).distinct()
        return queryset


class MigratedFilter(admin.SimpleListFilter):
    """
    Admin filter for migration status.

    Allows filtering words by whether they were migrated from v1 or created in v2.
    """

    title = _("migration status")
    parameter_name = "migrated"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
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
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
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
