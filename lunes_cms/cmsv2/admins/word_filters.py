from __future__ import absolute_import, annotations, unicode_literals

from typing import Iterable, TYPE_CHECKING

from django.contrib import admin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.areas import visible_jobs, visible_units
from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import ImageSource

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


class ImageSourceFilter(admin.SimpleListFilter):
    """
    Filter for displaying words by where their image came from.

    A word matches if its own image or one of its unit images has that source.
    """

    title = _("Image source")
    parameter_name = "image_source"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        return [
            (source.value, source.label)
            for source in ImageSource
            if source != ImageSource.UNKNOWN
        ]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        if not self.value():
            return queryset
        return queryset.filter(
            Q(image_source=self.value())
            | Q(unit_word_relations__image_source=self.value())
        ).distinct()


class JobDropdownFilter(admin.SimpleListFilter):
    """Filter for displaying the words of a job in the admin interface."""

    title = _("Job")
    parameter_name = "job"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        return [(str(job.pk), job.name) for job in visible_jobs(request.user)]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        if value := self.value():
            return queryset.filter(units__jobs__id=value).distinct()
        return queryset


class UnitDropdownFilter(admin.SimpleListFilter):
    """
    Filter for displaying the words of a unit in the admin interface.

    If a job is selected in :class:`JobDropdownFilter`, only the units of this
    job are offered.
    """

    title = _("Unit")
    parameter_name = "unit"

    def __init__(
        self,
        request: HttpRequest,
        params: dict[str, list[str]],
        model: type[Word],
        model_admin: admin.ModelAdmin[Word],
    ) -> None:
        super().__init__(request, params, model, model_admin)
        # Ignore a selected unit that does not belong to the selected job,
        # e.g. because the job was changed after the unit had been selected.
        if self.value() not in {key for key, _title in self.lookup_choices}:
            self.used_parameters.pop(self.parameter_name, None)

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Word]
    ) -> Iterable[tuple[str, _StrOrPromise]]:
        units = visible_units(request.user)
        job_id = request.GET.get(JobDropdownFilter.parameter_name)
        if job_id and job_id.isdigit():
            units = units.filter(jobs__id=job_id).distinct()
        return [(str(unit.pk), unit.title) for unit in units]

    def queryset(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> QuerySet[Word] | None:
        if value := self.value():
            return queryset.filter(units__id=value).distinct()
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
