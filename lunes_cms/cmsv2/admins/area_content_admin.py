from __future__ import absolute_import, annotations, unicode_literals

from typing import Any, TYPE_CHECKING

from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.http import HttpRequest

from ..areas import administered_areas, default_area
from .base import BaseAdmin

if TYPE_CHECKING:
    from django.db.models import Field, ForeignKey, Model
    from django.forms import ModelChoiceField, ModelForm


class AreaContentAdmin(BaseAdmin):
    """
    Base admin class for content that belongs to an area: jobs, units and
    words.

    It decides who may pick the area of the content and which area new
    content is put into, see :func:`~lunes_cms.cmsv2.areas.default_area`.
    """

    def get_readonly_fields(
        self, request: HttpRequest, obj: Model | None = None
    ) -> list[str]:
        """
        Only superusers may move content between areas.

        An area administrator who administers several areas still has to pick
        one when creating content, so the field stays editable on the add form —
        limited to their own areas, see :meth:`formfield_for_foreignkey`.
        """
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if request.user.is_superuser:
            return readonly_fields
        if obj is None and len(administered_areas(request.user)) > 1:
            return readonly_fields
        return [*readonly_fields, "area"]

    def get_form(
        self,
        request: HttpRequest,
        obj: Model | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type["ModelForm[Any]"]:
        """
        Preselect the default area of the user on the add form.

        The form takes the initial value of the field from its instance, so
        the fresh instance of the add form is created with the default area
        right away. That covers the editable field as well as the read-only
        one (see :meth:`get_readonly_fields`), which only ever displays the
        instance's own ``area``.
        """
        form = super().get_form(request, obj, change, **kwargs)
        if obj is not None:
            return form
        area = default_area(request.user)

        class PreselectedAreaForm(form):  # type: ignore[misc,valid-type]
            """``form``, with a fresh instance already pointed at the area."""

            def __init__(self, *args: Any, **inner_kwargs: Any) -> None:
                if inner_kwargs.get("instance") is None:
                    inner_kwargs["instance"] = self._meta.model(area=area)
                super().__init__(*args, **inner_kwargs)

        return PreselectedAreaForm

    def formfield_for_foreignkey(
        self,
        db_field: "ForeignKey[Any, Any]",
        request: HttpRequest,
        **kwargs: Any,
    ) -> "ModelChoiceField[Any] | None":
        """
        Offer an area administrator only the areas they administer.

        The area cannot be emptied, so content created by an area
        administrator never ends up in the wrong area by accident.
        """
        if db_field.name == "area" and not request.user.is_superuser:
            areas = administered_areas(request.user)
            if areas.exists():
                kwargs["queryset"] = areas
                kwargs["required"] = True
                kwargs["empty_label"] = None
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(
        self, db_field: "Field[Any, Any]", request: HttpRequest, **kwargs: Any
    ) -> Any:
        """
        Switch off the add/change/delete/view-related icons of the area field.

        ``formfield_for_foreignkey`` builds the plain field; the base
        implementation of this method is what wraps it with those icons
        afterwards, so it is only here, once that wrapping has happened,
        that they can be turned back off. Managing an entire area from a
        content edit form is a shortcut nobody needs here, and a confusing (in
        the delete case, dangerous) one to leave lying around; the area
        change and list pages are one click away regardless.
        """
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        widget = getattr(formfield, "widget", None)
        if db_field.name == "area" and isinstance(widget, RelatedFieldWidgetWrapper):
            widget.can_add_related = False
            widget.can_change_related = False
            widget.can_delete_related = False
            widget.can_view_related = False
        return formfield

    def save_model(
        self,
        request: HttpRequest,
        obj: Any,
        form: "ModelForm[Model]",
        change: bool,
    ) -> None:
        """
        Put new content of a single-area administrator into their area.

        Administrators of a single area never see the field — it is
        read-only for them, see :meth:`get_readonly_fields` — so their area
        never reaches the form. It is filled in here, the same way
        ``created_by`` is, in case the instance did not come from
        :meth:`get_form`.
        """
        if not change and not request.user.is_superuser:
            areas = list(administered_areas(request.user))
            if len(areas) == 1:
                obj.area = areas[0]
        super().save_model(request, obj, form, change)
