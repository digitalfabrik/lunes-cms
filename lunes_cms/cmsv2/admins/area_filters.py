from __future__ import absolute_import, annotations, unicode_literals

from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest

from ..areas import administered_areas, scope_jobs
from ..models import Area, Job

if TYPE_CHECKING:
    from django.db.models import Field
    from django.utils.functional import _StrPromise


class AreaListFilter(admin.RelatedFieldListFilter):
    """
    Filter for the area of a job that only offers the areas the user may see.
    """

    def field_choices(
        self,
        field: "Field[Any, Any]",
        request: HttpRequest,
        model_admin: admin.ModelAdmin[Any],
    ) -> list[tuple[str, "str | _StrPromise"]]:
        areas = (
            Area.objects.all()
            if request.user.is_superuser
            else administered_areas(request.user)
        )
        return [(str(area.pk), str(area)) for area in areas]


class JobListFilter(admin.RelatedFieldListFilter):
    """
    Filter for the job of a unit that only offers the jobs the user may see, so
    the names of the jobs of other areas do not leak through the filter.
    """

    def field_choices(
        self,
        field: "Field[Any, Any]",
        request: HttpRequest,
        model_admin: admin.ModelAdmin[Any],
    ) -> list[tuple[str, "str | _StrPromise"]]:
        jobs = scope_jobs(Job.objects.all(), request.user).order_by("name")
        return [(str(job.pk), str(job)) for job in jobs]
