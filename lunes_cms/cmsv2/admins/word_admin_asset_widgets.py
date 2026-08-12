from __future__ import absolute_import, annotations, unicode_literals

from typing import TYPE_CHECKING

from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.utils import (
    cache_busted_url,
    example_sentence_generate_html,
    get_image_tag,
    is_not_blank,
)
from lunes_cms.core import settings

if TYPE_CHECKING:
    # `_StrOrPromise` only exists in django-stubs, not at runtime.
    from django.utils.functional import _StrOrPromise


class WordAdminAssetWidgetsMixin:
    """
    Mixin providing the change-page widgets for (re)generating and
    previewing a word's audio, image and example sentence assets via OpenAI.
    """

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
