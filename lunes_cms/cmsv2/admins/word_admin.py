from __future__ import absolute_import, annotations, unicode_literals

from datetime import date
from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import lazy
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.admins.word_filters import (
    HasCompleteExampleSentenceFilter,
    HasImageFilter,
    MigratedFilter,
    UnitOrJobDropdownFilter,
)
from lunes_cms.cmsv2.models import AlternativeWord, Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.utils import (
    cache_busted_url,
    example_sentence_generate_html,
    get_image_tag,
    is_not_blank,
)
from lunes_cms.core import settings

if TYPE_CHECKING:
    # These only exist in django-stubs, not at runtime.
    from django.contrib.admin.options import _FieldGroups
    from django.utils.functional import _StrOrPromise

_format_html_lazy = lazy(format_html, SafeString)


class AlternativeWordInline(admin.TabularInline):
    """
    Inline admin for the AlternativeWord model.

    This inline allows editing alternative words directly from the Word admin page.
    """

    model = AlternativeWord
    extra = 1
    can_delete = False
    verbose_name = _("alternative word")
    verbose_name_plural = _format_html_lazy("<h2>{}</h2>", _("Alternative Words"))
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


class UnitInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing unit-word relationships directly from the Word admin page,
    including the ability to add/edit images and audio for each unit-word relation.
    """

    model = UnitWordRelation
    verbose_name_plural = _format_html_lazy("<h2>{}</h2>", _("Unit-Word Relations"))
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


class WordAdmin(BaseAdmin):
    """
    Admin interface for the Word model.

    This admin class provides a comprehensive interface for managing words,
    including their attributes, audio files, images, and relationships with units.
    It includes custom display methods for showing and managing assets.
    """

    fieldsets = (
        (
            _format_html_lazy("<h2>{}</h2>", _("Word Information")),
            {
                "fields": (
                    "word_type",
                    "grammatical_gender",
                    "singular_article",
                    "word",
                    "plural_article",
                    "plural",
                    "migrated_status",
                )
            },
        ),
        (
            _format_html_lazy("<h2>{}</h2>", _("Pronunciation")),
            {"fields": ("pronunciation",)},
        ),
        (
            _format_html_lazy("<h2>{}</h2>", _("Audio")),
            {
                "fields": (
                    "audio",
                    "audio_player",
                    "audio_generate",
                    "audio_check_status",
                )
            },
        ),
        (
            _format_html_lazy("<h2>{}</h2>", _("Image")),
            {
                "fields": (
                    "image",
                    "image_check_status",
                    "image_generate",
                    "image_tag",
                )
            },
        ),
        (
            _format_html_lazy("<h2>{}</h2>", _("Example Sentence")),
            {
                "fields": (
                    "example_sentence",
                    "example_sentence_generate",
                    "example_sentence_check_status",
                    "example_sentence_audio",
                    "example_sentence_audio_player",
                    "example_sentence_audio_generate",
                )
            },
        ),
    )
    readonly_fields = (
        "audio_generate",
        "audio_player",
        "example_sentence_audio_generate",
        "example_sentence_audio_player",
        "example_sentence_generate",
        "created_by",
        "created_by_user",
        "image_generate",
        "image_tag",
        "migrated_status",
    )
    search_fields = ["word"]
    ordering = ["word", "creation_date"]
    inlines = [AlternativeWordInline, UnitInline]
    list_display = (
        "word",
        "migrated_status",
        "word_type",
        "singular_article_display",
        "list_audio",
        "list_image",
        "creator_group",
        "created_by_user",
        "creation_date_display",
    )
    list_filter = [
        "word_type",
        "audio_check_status",
        "image_check_status",
        HasImageFilter,
        UnitOrJobDropdownFilter,
        HasCompleteExampleSentenceFilter,
        MigratedFilter,
        "created_by",
    ]
    list_select_related = ["created_by", "created_by_user"]
    list_per_page = 25

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the word admin interface,
        including scripts for asset management, audio playback, and status updates.
        """

        js = [
            "js/cookies.js",
            "js/word_image_asset_config.js",
            "js/unitword_image_asset_config.js",
            "js/asset_manager.js",
            "js/word_audio_asset_config.js",
            "js/audio_asset_manager.js",
            "js/audio_player.js",
            "js/audio_check_status_update.js",
            "js/image_check_status_update.js",
            "js/generate_example_sentence.js",
            "js/inline_regenerate.js",
            "js/alternative_word_actions.js",
        ]
        css = {"all": ["css/asset_manager.css", "css/audio_player.css"]}

    def _render_regenerate_widget(  # pylint: disable=too-many-arguments
        self,
        *,
        asset_type: str,
        generate_url: str,
        store_url: str,
        text_field: str,
        text_value: _StrOrPromise,
        store_field: str,
        current_preview: _StrOrPromise,
        generate_label: _StrOrPromise,
        regenerate_label: _StrOrPromise,
        with_additional_info: bool = False,
        spoken_text: str = "",
    ) -> SafeString:
        """
        Render an inline (re)generation widget for the change page.

        The widget generates a new audio file or image via OpenAI without
        leaving the page, shows the current and the newly generated version
        side by side for comparison, and lets the user keep the new one or
        discard it and keep the current one.

        ``spoken_text`` is shown above the buttons as a reminder to save first.
        """
        spoken_text_html: _StrOrPromise = ""
        if spoken_text:
            spoken_text_html = format_html(
                '<div class="regen-spoken-text">{} „{}“</div>',
                _("Will be spoken:"),
                spoken_text,
            )

        additional_info_html: _StrOrPromise = ""
        if with_additional_info:
            additional_info_html = format_html(
                '<div class="regen-allow-text-row">'
                '<label><input type="checkbox" class="regen-allow-text"> {}</label>'
                "</div>"
                '<div class="regen-additional-info-row">'
                "<label>{} "
                '<input type="text" class="regen-additional-info"></label>'
                "</div>",
                _(
                    "Allow text/numbers in the image (e.g. for a receipt or a clock face)"
                ),
                _("Additional info (optional)"),
            )

        return format_html(
            '<div class="inline-regenerate" data-asset-type="{asset_type}" '
            'data-generate-url="{generate_url}" data-store-url="{store_url}" '
            'data-text-field="{text_field}" data-text="{text_value}" '
            'data-store-field="{store_field}">'
            '<div class="regen-compare">'
            '<div class="regen-col regen-current">'
            '<div class="regen-col-label">{current_label}</div>'
            '<div class="regen-current-preview">{current_preview}</div>'
            "</div>"
            '<div class="regen-col regen-new">'
            '<div class="regen-col-label">{new_label}</div>'
            '<div class="regen-new-empty">{empty_label}</div>'
            '<div class="regen-new-preview"></div>'
            "</div>"
            "</div>"
            "{spoken_text_html}"
            "{additional_info_html}"
            '<div class="regen-toolbar">'
            '<button type="button" class="btn btn-primary btn-sm regen-generate-btn" '
            'data-regenerate-label="{regenerate_label}">{generate_label}</button>'
            '<span class="regen-spinner spinner-border spinner-border-sm is-hidden"></span>'
            '<span class="regen-message"></span>'
            "</div>"
            '<div class="regen-decision is-hidden">'
            '<button type="button" class="btn btn-success btn-sm regen-keep-btn">{keep_label}</button> '
            '<button type="button" class="btn btn-secondary btn-sm regen-discard-btn">{discard_label}</button>'
            "</div>"
            "</div>",
            asset_type=asset_type,
            generate_url=generate_url,
            store_url=store_url,
            text_field=text_field,
            text_value=text_value,
            store_field=store_field,
            current_label=_("Current"),
            new_label=_("New"),
            empty_label=_("Not generated yet"),
            current_preview=current_preview,
            spoken_text_html=spoken_text_html,
            additional_info_html=additional_info_html,
            generate_label=generate_label,
            regenerate_label=regenerate_label,
            keep_label=_("Keep new"),
            discard_label=_("Discard new"),
        )

    def audio_generate(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the inline audio (re)generation widget.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the audio generation widget
        """
        if not obj.pk:
            return _("Save to enable audio generation.")
        current_preview: _StrOrPromise
        if obj.audio:
            current_preview = format_html(
                "<audio controls src='{}'></audio>", cache_busted_url(obj.audio)
            )
        else:
            current_preview = _("No audio yet.")
        return self._render_regenerate_widget(
            asset_type="audio",
            generate_url=reverse("cmsv2:word_generate_audio_via_openai", args=[obj.pk]),
            store_url=reverse(
                "cmsv2:word_store_generated_audio_permanently", args=[obj.pk]
            ),
            text_field="word_text",
            text_value=obj.text_for_audio_generation(),
            store_field="temp_audio_filename",
            current_preview=current_preview,
            generate_label=_("Generate audio"),
            regenerate_label=_("Regenerate audio"),
            spoken_text=obj.text_for_audio_generation(),
        )

    audio_generate.short_description = _("Audio Generation")  # type: ignore[attr-defined]

    def audio_player(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the audio player preview.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the audio player
        """
        if obj.audio:
            return format_html(
                "<audio controls id='audio_preview_player' src='{}'></audio>",
                cache_busted_url(obj.audio),
            )
        return "No audio file uploaded."

    audio_player.short_description = "Audio Preview"  # type: ignore[attr-defined]

    def example_sentence_generate(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the inline example sentence generation widget.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the example sentence generation widget
        """
        if obj.pk:
            return example_sentence_generate_html(
                generate_url=reverse(
                    "cmsv2:word_generate_example_sentence_via_openai", args=[obj.pk]
                ),
                store_url=reverse(
                    "cmsv2:word_store_generated_example_sentence", args=[obj.pk]
                ),
                target="id_example_sentence",
            )
        return _("Save to enable example sentence generation.")

    example_sentence_generate.short_description = _("Example Sentence Generation")  # type: ignore[attr-defined]

    def example_sentence_audio_generate(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the inline example sentence audio (re)generation widget.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the audio generation widget
        """
        if not obj.pk or not is_not_blank(obj.example_sentence):
            return _("Save to enable audio generation.")
        current_preview: _StrOrPromise
        if obj.example_sentence_audio:
            current_preview = format_html(
                "<audio controls src='{}'></audio>",
                cache_busted_url(obj.example_sentence_audio),
            )
        else:
            current_preview = _("No audio yet.")
        return self._render_regenerate_widget(
            asset_type="audio",
            generate_url=reverse(
                "cmsv2:word_generate_example_sentence_audio_via_openai", args=[obj.pk]
            ),
            store_url=reverse(
                "cmsv2:word_store_generated_example_sentence_audio_permanently",
                args=[obj.pk],
            ),
            text_field="example_sentence_text",
            text_value=obj.example_sentence,
            store_field="temp_audio_filename",
            current_preview=current_preview,
            generate_label=_("Generate audio"),
            regenerate_label=_("Regenerate audio"),
        )

    example_sentence_audio_generate.short_description = _("Example Sentence Audio Generation")  # type: ignore[attr-defined]

    def example_sentence_audio_player(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the example sentence audio player preview.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the audio player
        """
        if obj.example_sentence_audio:
            return format_html(
                "<audio controls id='example_sentence_audio_preview_player' src='{}'></audio>",
                cache_busted_url(obj.example_sentence_audio),
            )
        return "No audio file uploaded."

    example_sentence_audio_player.short_description = "Example Sentence Audio Preview"  # type: ignore[attr-defined]

    def image_tag(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for displaying the word's image with hover-to-enlarge functionality.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the image with hover overlay
        """
        if obj.image:
            return format_html(
                """<div class="image-hover-container">
                    <a href="{}" target="_blank">{}</a>
                    <div class="image-hover-overlay">
                        <img src="{}" alt="{}">
                    </div>
                </div>""",
                f"{settings.MEDIA_URL}{obj.image}",
                mark_safe(get_image_tag(obj.image, width=120)),
                f"{settings.MEDIA_URL}{obj.image}",
                escape(obj.word),
            )
        return "No image uploaded."

    image_tag.short_description = _("Image Preview")  # type: ignore[attr-defined]

    def image_generate(self, obj: Word) -> _StrOrPromise:
        """
        Generate HTML for the inline image (re)generation widget.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the image generation widget
        """
        if not obj.pk:
            return _("Save to enable image generation.")
        current_preview: _StrOrPromise
        if obj.image:
            current_preview = format_html(
                '<img src="{}" alt="{}" style="max-width: min(200px, 100%);">',
                f"{settings.MEDIA_URL}{obj.image}",
                obj.word,
            )
        else:
            current_preview = _("No image yet.")
        return self._render_regenerate_widget(
            asset_type="image",
            generate_url=reverse("cmsv2:generate_image_via_openai"),
            store_url=reverse(
                "cmsv2:word_store_generated_image_permanently", args=[obj.pk]
            ),
            text_field="word_text",
            text_value=obj.word,
            store_field="temp_filename",
            current_preview=current_preview,
            generate_label=_("Generate image"),
            regenerate_label=_("Regenerate image"),
            with_additional_info=True,
        )

    image_generate.short_description = _("Image Generation")  # type: ignore[attr-defined]

    def creator_group(self, obj: Word) -> str | None:
        """
        Determine the creator group for display in the admin interface.

        Args:
            obj: The word object

        Returns:
            str or None: "Admin" if created by an admin, the group name if created by a group,
                         or None if no creator information is available
        """
        if obj.creator_is_admin:
            return "Admin"
        if obj.created_by:
            return str(obj.created_by)
        return None

    creator_group.short_description = _("group")  # type: ignore[attr-defined]

    def list_audio(self, obj: Word) -> SafeString:
        """
        Generate HTML for displaying the word's audio with controls in the admin list view.

        This method creates HTML that includes an audio player and buttons for adding,
        replacing, or deleting the audio file, as well as a dropdown for the audio check status.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for displaying the word's audio with controls
        """
        audio_html = ""
        if obj.audio:
            audio_html = f"""
            <div class="audio-player-container">
                <audio class="minimal-audio-player"><source src="{cache_busted_url(obj.audio)}" type="audio/mpeg"></audio>
                <div class="play-btn">
                    <div>
                        <i class="fas fa-play"></i>
                    </div>
                </div>
                <div class="pause-btn" style="display: none;">
                    <div>
                        <i class="fas fa-pause"></i>
                    </div>
                </div>
            </div>
            """

        add_title = _("Add audio")
        upload_title = _("Upload audio")
        delete_title = _("Delete audio")
        controls_html = f"""
        <div class="audio-asset-controls" data-word-id="{obj.id}">
            <button type="button" class="add-audio-btn" style="display: {'none' if obj.audio else 'inline-flex'};" title="{add_title}">
                <span class="audio-add">+</span>
            </button>
            <button type="button" class="replace-audio-btn" style="display: {'inline-flex' if obj.audio else 'none'};" title="{upload_title}">
                <span class="audio-replace"><i class="fas fa-upload"></i></span>
            </button>
            <button type="button" class="delete-audio-btn" style="display: {'inline-flex' if obj.audio else 'none'};" title="{delete_title}">
                <span class="audio-delete">×</span>
            </button>
            <input type="file" class="audio-file-input" style="display: none;" accept="audio/*">
        </div>
        """

        word_audio_container = (
            f'<div class="word-audio-container">{audio_html}{controls_html}</div>'
        )

        options = ""
        for value, display in CheckStatus.choices:
            selected = "selected" if obj.audio_check_status == value else ""
            options += f'<option value="{value}" {selected}>{display}</option>'

        html = word_audio_container
        if obj.audio:
            html += f"""
            <select name="audio_check_status_{obj.id}" data-word-id="{obj.id}" class="audio-check-status-select" style="margin-top: 8px;">
                {options}
            </select>
            """

        return mark_safe(html)

    list_audio.short_description = _("audio")  # type: ignore[attr-defined]

    def list_image(self, obj: Word) -> SafeString:
        """
        Generate HTML for displaying the word's images with controls in the admin list view.

        This method creates HTML that includes the word's main image and unit-specific images,
        along with controls for adding, replacing, or deleting images, and dropdowns for
        the image check status.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for displaying the word's images with controls
        """
        # Generate the word's main image container
        word_image_container = self._generate_word_image_container(obj)

        # Generate the unit-specific image containers
        unit_word_images = self._generate_unit_word_images(obj)

        # Combine all images into a single container
        all_images = f'<div class="all-images-container"><div>{word_image_container}</div><div>{unit_word_images}</div></div>'

        return mark_safe(all_images)

    def _generate_word_image_container(self, obj: Word) -> str:
        """
        Generate HTML for the word's main image container.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the word's main image container
        """
        if obj.image:
            image_html = f"""<div class="image-hover-container">
                <a href="{escape(f"{settings.MEDIA_URL}{obj.image}")}" target="_blank">{get_image_tag(obj.image, width=50)}</a>
                <div class="image-hover-overlay">
                    <img src="{escape(f"{settings.MEDIA_URL}{obj.image}")}" alt="{escape(obj.word)}">
                </div>
            </div>"""
        else:
            image_html = ""

        add_title = _("Add image")
        upload_title = _("Upload image")
        delete_title = _("Delete image")
        controls_html = f"""
        <div class="image-controls" data-word-id="{obj.id}">
            <button type="button" class="add-image-btn" style="display: {'none' if obj.image else 'inline-flex'};" title="{add_title}">
                <span class="image-add">+</span>
            </button>
            <button type="button" class="replace-image-btn" style="display: {'inline-flex' if obj.image else 'none'};" title="{upload_title}">
                <span class="image-replace"><i class="fas fa-upload"></i></span>
            </button>
            <button type="button" class="delete-image-btn" style="display: {'inline-flex' if obj.image else 'none'};" title="{delete_title}">
                <span class="image-delete">×</span>
            </button>
            <input type="file" class="image-file-input" style="display: none;" accept="image/*">
        </div>
        """

        word_options = ""
        for value, display in CheckStatus.choices:
            selected = "selected" if obj.image_check_status == value else ""
            word_options += f'<option value="{value}" {selected}>{display}</option>'

        word_image_check_status_html = f"""
        <select name="image_check_status_{obj.id}" data-word-id="{obj.id}" class="image-check-status-select" style="margin-top: 8px;">
            {word_options}
        </select>
        """

        html = f'<div class="word-image-container">{image_html}{controls_html}</div>'
        if obj.image:
            html += word_image_check_status_html

        return html

    def _generate_unit_word_images(self, obj: Word) -> str:
        """
        Generate HTML for the unit-specific image containers.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for all unit-specific image containers
        """
        unit_word_images = ""

        for relation in obj.unit_word_relations.select_related("unit").all():
            unit_word_images += self._generate_unit_word_image(relation)

        return unit_word_images

    def _generate_unit_word_image(self, relation: UnitWordRelation) -> str:
        """
        Generate HTML for a single unit-word image container.

        Args:
            relation: The UnitWordRelation object

        Returns:
            str: HTML markup for a single unit-word image container
        """
        unit_name = relation.unit.title
        if relation.image:
            unit_image_html = f"""<div class="image-hover-container">
                <a href="{escape(f"{settings.MEDIA_URL}{relation.image}")}" target="_blank">{get_image_tag(relation.image, width=50)}</a>
                <div class="image-hover-overlay">
                    <img src="{escape(f"{settings.MEDIA_URL}{relation.image}")}" alt="{escape(relation.unit.title)}">
                </div>
            </div>"""
        else:
            unit_image_html = ""

        add_title = _("Add image")
        upload_title = _("Upload image")
        delete_title = _("Delete image")
        unit_controls_html = f"""
        <div class="unitword-image-controls" data-unitword-id="{relation.id}">
            <button type="button" class="add-unitword-image-btn" style="display: {'none' if relation.image else 'inline-flex'};" title="{add_title}">
                <span class="unitword-image-add">+</span>
            </button>
            <button type="button" class="replace-unitword-image-btn" style="display: {'inline-flex' if relation.image else 'none'};" title="{upload_title}">
                <span class="unitword-image-replace"><i class="fas fa-upload"></i></span>
            </button>
            <button type="button" class="delete-unitword-image-btn" style="display: {'inline-flex' if relation.image else 'none'};" title="{delete_title}">
                <span class="unitword-image-delete">×</span>
            </button>
            <input type="file" class="unitword-image-file-input" style="display: none;" accept="image/*">
        </div>
        """

        unit_options = ""
        for value, display in CheckStatus.choices:
            selected = "selected" if relation.image_check_status == value else ""
            unit_options += f'<option value="{value}" {selected}>{display}</option>'

        unit_image_check_status_html = f"""
        <select name="unitword_image_check_status_{relation.id}" data-unitword-id="{relation.id}" class="unitword-image-check-status-select" style="margin-top: 8px;">
            {unit_options}
        </select>
        """

        unit_name_html = f'<div class="unit-name">{unit_name}</div>'

        html = f"""
        <div class="unitword-image-wrapper">
            {unit_name_html}
            <div class="unitword-image-container">
                {unit_image_html}
                {unit_controls_html}
            </div>
        </div>
        """

        if relation.image:
            html += unit_image_check_status_html

        return html

    list_image.short_description = _("Image")  # type: ignore[attr-defined]

    def singular_article_display(self, obj: Word) -> str:
        """
        Format the singular article for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the singular article
        """
        return obj.get_singular_article_display()

    singular_article_display.short_description = _("singular article")  # type: ignore[attr-defined]

    def creation_date_display(self, obj: Word) -> date:
        """
        Format the creation date for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            date: The date portion of the creation_date timestamp
        """
        return obj.creation_date.date()

    creation_date_display.short_description = _("creation date")  # type: ignore[attr-defined]

    def migrated_status(self, obj: Word) -> SafeString:
        """
        Display a badge indicating whether the word was migrated from v1 or created in v2.

        Args:
            obj: The word object

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

    def audio_check_status_display(self, obj: Word) -> str:
        """
        Format the audio check status for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the audio check status
        """
        return obj.get_audio_check_status_display()

    audio_check_status_display.short_description = _("audio check status")  # type: ignore[attr-defined]
    audio_check_status_display.admin_order_field = "audio_check_status"  # type: ignore[attr-defined]

    def image_check_status_display(self, obj: Word) -> str:
        """
        Format the image check status for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the image check status
        """
        return obj.get_image_check_status_display()

    image_check_status_display.short_description = _("image check status")  # type: ignore[attr-defined]
    image_check_status_display.admin_order_field = "image_check_status"  # type: ignore[attr-defined]
