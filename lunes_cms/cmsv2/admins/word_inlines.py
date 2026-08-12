from __future__ import absolute_import, annotations, unicode_literals

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import AlternativeWord
from lunes_cms.cmsv2.models.unit import UnitWordRelation


class AlternativeWordInline(admin.TabularInline):
    """
    Inline admin for the AlternativeWord model.

    This inline allows editing alternative words directly from the Word admin page.
    """

    model = AlternativeWord
    extra = 1
    can_delete = False
    verbose_name = _("alternative word")
    verbose_name_plural = _("So heißt das auch")
    fields = [
        "grammatical_gender",
        "singular_article",
        "alt_word",
        "plural_article",
        "plural",
        "action_buttons",
    ]
    readonly_fields = ["action_buttons"]

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


class UnitInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing unit-word relationships directly from the Word admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
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
