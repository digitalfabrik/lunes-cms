from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..areas import administered_areas
from ..models import Area, Feedback, Job, Unit, Word

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.utils.functional import _StrPromise


class FeedbackAreaListFilter(admin.SimpleListFilter):
    """
    Filter for the area of the job, unit or word a feedback entry refers to.

    Feedback has no direct FK to an area (it refers to its content via a
    generic FK to a job, unit or word), so this collects the object ids of
    the given area for each of those three content types instead of using a
    :class:`~django.contrib.admin.RelatedFieldListFilter`, see
    :func:`~lunes_cms.cmsv2.feedback_filter.filter_feedback_by_area`.
    """

    title = _("area")
    parameter_name = "area"

    def lookups(
        self, request: HttpRequest, model_admin: admin.ModelAdmin[Any]
    ) -> list[tuple[str, "str | _StrPromise"]]:
        areas = (
            Area.objects.all()
            if request.user.is_superuser
            else administered_areas(request.user)
        )
        return [(str(area.pk), str(area)) for area in areas]

    def queryset(
        self, request: HttpRequest, queryset: "QuerySet[Feedback]"
    ) -> "QuerySet[Feedback]":
        value = self.value()
        if not value:
            return queryset

        area = Area.objects.filter(pk=value).first()
        if area is None:
            return queryset.none()

        job_type_id = ContentType.objects.get(app_label="cmsv2", model="job").id
        unit_type_id = ContentType.objects.get(app_label="cmsv2", model="unit").id
        word_type_id = ContentType.objects.get(app_label="cmsv2", model="word").id

        job_ids = Job.objects.filter(area=area).values_list("id", flat=True)
        unit_ids = Unit.objects.filter(jobs__area=area).values_list("id", flat=True)
        word_ids = Word.objects.filter(units__jobs__area=area).values_list(
            "id", flat=True
        )

        return queryset.filter(
            Q(content_type=job_type_id, object_id__in=job_ids)
            | Q(content_type=unit_type_id, object_id__in=unit_ids)
            | Q(content_type=word_type_id, object_id__in=word_ids)
        )
