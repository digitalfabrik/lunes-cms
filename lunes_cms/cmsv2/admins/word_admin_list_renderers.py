from __future__ import absolute_import, annotations, unicode_literals

from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.static import CheckStatus
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.utils import cache_busted_url, get_image_tag
from lunes_cms.core import settings


class WordAdminListRenderersMixin:
    """
    Mixin providing the ``list_display`` HTML renderers for the Word admin
    list view (audio, image and example sentence columns with their
    inline controls).
    """

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

        controls_html = f"""
        <div class="audio-asset-controls" data-word-id="{obj.id}">
            <button type="button" class="add-audio-btn" style="display: {'none' if obj.audio else 'inline-flex'};">
                <span class="audio-add">+</span>
            </button>
            <button type="button" class="replace-audio-btn" style="display: {'inline-flex' if obj.audio else 'none'};">
                <span class="audio-replace">↻</span>
            </button>
            <button type="button" class="delete-audio-btn" style="display: {'inline-flex' if obj.audio else 'none'};">
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

    list_image.short_description = _("Image")  # type: ignore[attr-defined]

    def list_example_sentence(self, obj: Word) -> SafeString:
        """
        Generate HTML for displaying the word's example sentence with controls in the admin list view.

        This method creates HTML that includes the word's example sentence (as text),
        along with controls for listening to the audio, uploading new audio and dropdowns for the check status.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for displaying the word's example sentence with controls
        """
        example_sentence_html = self._generate_word_example_sentence_container(obj)
        example_sentence_audio_html = (
            self._generate_word_example_sentence_audio_container(obj)
        )
        example_sentence_combined = f'<div class="example-sentence-container"><div>{example_sentence_html}</div><div>{example_sentence_audio_html}</div></div>'
        return mark_safe(example_sentence_combined)

    list_example_sentence.short_description = _("Example sentence")  # type: ignore[attr-defined]

    def _generate_example_sentence_text_html(
        self, sentence: str, truncate_at: int = 40
    ) -> str:
        """Generate HTML for an example sentence, truncated with an expandable
        "more" toggle if it exceeds `truncate_at` characters.

        Args:
            sentence: The raw example sentence text
            truncate_at: The character count above which the sentence gets truncated

        Returns:
            str: HTML markup for the (optionally truncated) example sentence
        """
        if len(sentence) <= truncate_at:
            return f"""<div class="example-sentence-hover-container">
                <span>{escape(sentence)}</span>
            </div>"""

        truncated = escape(sentence[:truncate_at])
        full = escape(sentence)
        return f"""<div class="example-sentence-hover-container py-2">
            <details class="example-sentence-details">
                <summary class="example-sentence-summary">
                    <span class="example-sentence-truncated">{truncated}&hellip;</span>
                    <span class="example-sentence-full">{full}</span>
                    <span class="example-sentence-more">{_("more")}</span>
                </summary>
            </details>
        </div>"""

    def _generate_word_example_sentence_container(self, obj: Word) -> str:
        """Generate HTML for the word's example sentence container.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the word's example sentence container"""

        example_sentence_html = (
            self._generate_example_sentence_text_html(obj.example_sentence)
            if obj.example_sentence
            else ""
        )

        controls_html = f"""
        <div class="example-sentence-controls" data-word-id="{obj.id}">
            <button type="button" class="edit-example-sentence-btn" style="display: {'inline-flex' if obj.example_sentence else 'none'};">
                <span class="example-sentence-edit">✎</span>
            </button>
            <button disabled type="button" class="replace-example-sentence-btn" style="display: {'inline-flex' if obj.example_sentence else 'none'};">
                <span class="example-sentence-replace">↻</span>
            </button>
            <button disabled type="button" class="delete-example-sentence-btn" style="display: {'inline-flex' if obj.example_sentence else 'none'};">
                <span class="example-sentence-delete">×</span>
            </button>
            <input type="file" class="example-sentence-file-input" style="display: none;" accept="example_sentence/*">
        </div>
        """

        display_html = f"""
        <div class="example-sentence-display">
            {example_sentence_html}{controls_html}
        </div>
        """

        edit_form_html = ""
        if obj.example_sentence:
            store_url = reverse(
                "cmsv2:word_store_generated_example_sentence", args=[obj.id]
            )
            edit_form_html = f"""
            <div class="example-sentence-edit-form" style="display: none;">
                <textarea class="example-sentence-textarea" rows="3" data-original-value="{escape(obj.example_sentence)}">{escape(obj.example_sentence)}</textarea>
                <div class="example-sentence-edit-controls">
                    <button type="button" class="save-example-sentence-btn" data-store-url="{store_url}">
                        <span class="example-sentence-save">✓</span>
                    </button>
                    <button type="button" class="cancel-example-sentence-btn">
                        <span class="example-sentence-cancel">×</span>
                    </button>
                </div>
            </div>
            """

        word_options = ""
        for value, display in CheckStatus.choices:
            selected = "selected" if obj.example_sentence_check_status == value else ""
            word_options += f'<option value="{value}" {selected}>{display}</option>'

        word_example_sentence_check_status_html = f"""
        <select name="example_sentence_check_status_{obj.id}" data-word-id="{obj.id}" class="example-sentence-check-status-select" style="margin-top: 8px;">
            {word_options}
        </select>
        """

        html = f'<div class="word-example-sentence-container">{display_html}{edit_form_html}</div>'
        if obj.example_sentence:
            html += word_example_sentence_check_status_html

        return html

    def _generate_word_example_sentence_audio_container(self, obj: Word) -> str:
        """Generate HTML for the word's example sentence audio container.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the word's example sentence audio container"""

        audio_html = ""
        if obj.example_sentence_audio:
            audio_html = f"""
            <div class="audio-player-container">
                <audio class="minimal-audio-player"><source src="{cache_busted_url(obj.example_sentence_audio)}" type="audio/mpeg"></audio>
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

        controls_html = f"""
        <div class="example-sentence-audio-controls" data-word-id="{obj.id}">
            <button disabled type="button" class="add-example-sentence-audio-btn" style="display: {'none' if obj.example_sentence_audio else 'inline-flex'};">
                <span class="example-sentence-audio-add">+</span>
            </button>
            <button disabled type="button" class="replace-example-sentence-audio-btn" style="display: {'inline-flex' if obj.example_sentence_audio else 'none'};">
                <span class="example-sentence-audio-replace">↻</span>
            </button>
            <button disabled type="button" class="delete-example-sentence-audio-btn" style="display: {'inline-flex' if obj.example_sentence_audio else 'none'};">
                <span class="example-sentence-audio-delete">×</span>
            </button>
            <input type="file" class="example-sentence-audio-file-input" style="display: none;" accept="audio/*">
        </div>
        """

        return f'<div class="word-example-sentence-audio-container py-2">{audio_html}{controls_html}</div>'

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

        controls_html = f"""
        <div class="image-controls" data-word-id="{obj.id}">
            <button type="button" class="add-image-btn" style="display: {'none' if obj.image else 'inline-flex'};">
                <span class="image-add">+</span>
            </button>
            <button type="button" class="replace-image-btn" style="display: {'inline-flex' if obj.image else 'none'};">
                <span class="image-replace">↻</span>
            </button>
            <button type="button" class="delete-image-btn" style="display: {'inline-flex' if obj.image else 'none'};">
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

        unit_controls_html = f"""
        <div class="unitword-image-controls" data-unitword-id="{relation.id}">
            <button type="button" class="add-unitword-image-btn" style="display: {'none' if relation.image else 'inline-flex'};">
                <span class="unitword-image-add">+</span>
            </button>
            <button type="button" class="replace-unitword-image-btn" style="display: {'inline-flex' if relation.image else 'none'};">
                <span class="unitword-image-replace">↻</span>
            </button>
            <button type="button" class="delete-unitword-image-btn" style="display: {'inline-flex' if relation.image else 'none'};">
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
