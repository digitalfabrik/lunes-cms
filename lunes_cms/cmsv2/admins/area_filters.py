from __future__ import absolute_import, annotations, unicode_literals

from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

from ..areas import administered_areas, visible_jobs
from ..models import Area

if TYPE_CHECKING:
    from django.db.models import Field, Model
    from django.utils.functional import _StrPromise


class AreaListFilter(admin.RelatedFieldListFilter):
    """
    Filter for the area of a job, unit or word that only offers the areas the
    user may see.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        field: "Field[Any, Any]",
        request: HttpRequest,
        params: dict[str, list[str]],
        model: type[Model],
        model_admin: admin.ModelAdmin[Any],
        field_path: str,
    ) -> None:
        self.is_superuser = request.user.is_superuser
        super().__init__(field, request, params, model, model_admin, field_path)
        self.empty_value_display = escape(_("no area"))

    @property
    def include_empty_choice(self) -> bool:
        """Offer the content without an area to superusers only."""
        return self.is_superuser and super().include_empty_choice

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
        jobs = visible_jobs(request.user).order_by("name")
        return [(str(job.pk), str(job)) for job in jobs]
