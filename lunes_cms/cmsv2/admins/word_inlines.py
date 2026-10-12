from __future__ import absolute_import, annotations, unicode_literals

from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest
from django.utils.functional import lazy
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.areas import (
    area_conflict_message,
    area_of_unit,
    find_area_conflict,
)
from lunes_cms.cmsv2.models import AlternativeWord, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation

if TYPE_CHECKING:
    # `_FieldGroups` only exists in django-stubs, not at runtime.
    from django.contrib.admin.options import _FieldGroups

format_html_lazy = lazy(format_html, SafeString)


class AlternativeWordInline(admin.TabularInline):
    """
    Inline admin for the AlternativeWord model.

    This inline allows editing alternative words directly from the Word admin page.
    """

    model = AlternativeWord
    extra = 1
    can_delete = False
    verbose_name = _("alternative word")
    verbose_name_plural = format_html_lazy("<h2>{}</h2>", _("Alternative Words"))
    fields = [
        "grammatical_gender",
        "singular_article",
        "alt_word",
        "plural_article",
        "plural",
        "action_buttons",
    ]
    readonly_fields = ["action_buttons"]

    def get_max_num(
        self, request: HttpRequest, obj: Word | None = None, **kwargs: Any
    ) -> int | None:
        """
        Limit the formset to the existing rows plus the ``extra`` empty rows
        on the change page, so Django hides its "Add another" link there.
        New rows are added instantly via the "+" button instead, which
        reloads the page with a fresh empty row. On the add page (no
        ``obj``), the default is kept so multiple rows can be added before
        the first save.

        Args:
            request: The current request
            obj: The word object, or None on the add page

        Returns:
            int or None: The maximum number of forms in the formset
        """
        if obj:
            return obj.alternative_words.count() + self.extra
        return super().get_max_num(request, obj, **kwargs)

    def get_fields(self, request: HttpRequest, obj: Word | None = None) -> _FieldGroups:
        """
        Hide the action buttons from users who may only view words, because
        their requests to add, save or delete would be denied anyway.
        """
        fields = super().get_fields(request, obj)
        if not self.has_change_permission(request, obj):
            return [field for field in fields if field != "action_buttons"]
        return fields

    def has_view_permission(
        self, request: HttpRequest, _obj: Word | None = None
    ) -> bool:
        return request.user.has_perm("cmsv2.view_word") or self.has_change_permission(
            request
        )

    def has_add_permission(
        self, request: HttpRequest, _obj: Word | None = None
    ) -> bool:
        return self.has_change_permission(request)

    def has_change_permission(
        self, request: HttpRequest, _obj: Word | None = None
    ) -> bool:
        return request.user.has_perm("cmsv2.change_word")

    def action_buttons(self, obj: AlternativeWord) -> SafeString:
        """
        Render buttons which instantly add, save or delete the alternative
        word of the row, so no separate save of the whole word is needed.

        Args:
            obj: The alternative word object

        Returns:
            str: HTML markup for the action buttons
        """
        if not obj.pk:
            return format_html(
                '<button type="button" class="add-alternative-word-btn" title="{}">'
                '<span class="alternative-word-add">+</span></button>',
                _("Add alternative word"),
            )
        return format_html(
            '<button type="button" class="save-alternative-word-btn" '
            'data-alternative-word-id="{}" title="{}">'
            '<span class="alternative-word-save">✓</span></button>'
            '<button type="button" class="delete-alternative-word-btn" '
            'data-alternative-word-id="{}" title="{}">'
            '<span class="alternative-word-delete">×</span></button>',
            obj.pk,
            _("Save alternative word"),
            obj.pk,
            _("Delete alternative word"),
        )

    action_buttons.short_description = ""  # type: ignore[attr-defined]


class UnitInlineFormSet(BaseInlineFormSet):
    """
    Formset that keeps a word inside a single area.

    An already-saved row is checked against the word's other saved units by
    ``UnitWordRelation.clean()``. Two *new* rows are never each other's
    "already-saved" unit while validated, so this compares them too.
    """

    def clean(self) -> None:
        super().clean()
        new_rows = [
            (form, form.cleaned_data["unit"])
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and not form.instance.pk
            and form.cleaned_data.get("unit")
        ]
        conflict = find_area_conflict([unit for _form, unit in new_rows])
        if conflict is None:
            return
        existing_unit, new_unit = conflict
        conflicting_form = next(
            form for form, unit in new_rows if unit.pk == new_unit.pk
        )
        conflicting_form.add_error(
            "unit",
            area_conflict_message(
                self.instance, area_of_unit(existing_unit), area_of_unit(new_unit)
            ),
        )


class UnitInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing unit-word relationships directly from the Word admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
    formset = UnitInlineFormSet
    verbose_name_plural = format_html_lazy("<h2>{}</h2>", _("Unit-Word Relations"))
    extra = 1
    autocomplete_fields = ["unit"]
    fields = [
        "unit",
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
