from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.urls import reverse
from django.utils.html import mark_safe, format_html, escape
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.models import Job
from lunes_cms.cmsv2.models.static import Static
from lunes_cms.cmsv2.models.unit import UnitWordRelation, Unit
from lunes_cms.cmsv2.utils import get_image_tag
from lunes_cms.core import settings


class UnitOrJobDropdownFilter(admin.SimpleListFilter):
    """Filter for displaying units or jobs in the admin interface."""

    title = _("Unit or Job")
    parameter_name = "unit_or_job_choice"

    def lookups(self, request, model_admin):
        options = []
        for unit in Unit.objects.all():
            options.append((f"unit_{unit.pk}", f"Unit: {unit.title}"))
        for job in Job.objects.all():
            options.append((f"job_{job.pk}", f"Job: {job.name}"))
        return options

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        if value.startswith("unit_"):
            unit_id = value.split("_", 1)[1]
            return queryset.filter(units__id=unit_id).distinct()

        if value.startswith("job_"):
            job_id = value.split("_", 1)[1]
            return queryset.filter(units__jobs__id=job_id).distinct()

        return queryset


class UnitInline(admin.TabularInline):
    """
    Inline admin for UnitWordRelation model.

    This inline allows editing unit-word relationships directly from the Word admin page,
    including the ability to add/edit images for each unit-word relation.
    """

    model = UnitWordRelation
    extra = 1
    fields = [
        "unit",
        "image",
        "list_image",
        "image_check_status",
        "generate_image_link",
    ]
    readonly_fields = ["list_image", "generate_image_link"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


class WordAdmin(BaseAdmin):
    """
    Admin interface for the Word model.

    This admin class provides a comprehensive interface for managing words,
    including their attributes, audio files, images, and relationships with units.
    It includes custom display methods for showing and managing assets.
    """

    fields = (
        "word_type",
        "grammatical_gender",
        "singular_article",
        "word",
        "plural_article",
        "plural",
        "audio",
        "audio_player",
        "audio_generate",
        "audio_check_status",
        "image",
        "image_check_status",
        "image_generate",
        "image_tag",
        "definition",
        "additional_meaning_1",
        "additional_meaning_2",
    )
    readonly_fields = (
        "audio_generate",
        "audio_player",
        "created_by",
        "image_generate",
        "image_tag",
    )
    search_fields = ["word"]
    ordering = ["word", "creation_date"]
    inlines = [UnitInline]
    list_display = (
        "word",
        "word_type",
        "singular_article_display",
        "list_audio",
        "list_image",
        "creator_group",
        "creation_date_display",
    )
    list_filter = [
        "word_type",
        "audio_check_status",
        "image_check_status",
        UnitOrJobDropdownFilter,
    ]
    list_per_page = 25

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the word admin interface,
        including scripts for asset management, audio playback, and status updates.
        """

        js = [
            "js/word_image_asset_config.js",
            "js/unitword_image_asset_config.js",
            "js/asset_manager.js",
            "js/word_audio_asset_config.js",
            "js/audio_asset_manager.js",
            "js/audio_player.js",
            "js/audio_check_status_update.js",
            "js/image_check_status_update.js",
        ]
        css = {"all": ["css/asset_manager.css", "css/audio_player.css"]}

    def audio_generate(self, obj):
        """
        Generate HTML for the audio generation button.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the audio generation button
        """
        if obj.pk:
            url = reverse("cmsv2:word_generate_audio", args=[obj.pk])
            return format_html('<a class="button" href="{}">Generate Audio</a>', url)
        return "Save to enable audio generation."

    audio_generate.short_description = "Audio Generation"

    def audio_player(self, obj):
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
                obj.audio.url,
            )
        return "No audio file uploaded."

    audio_player.short_description = "Audio Preview"

    def image_generate(self, obj):
        """
        Generate HTML for the image generation button.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for the image generation button
        """
        if obj.pk:
            url = reverse("cmsv2:word_generate_image", args=[obj.pk])
            return format_html('<a class="button" href="{}">Generate Image</a>', url)
        return "Save to enable image generation."

    image_generate.short_description = "Image Generation"

    def creator_group(self, obj):
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
            return obj.created_by
        return None

    creator_group.short_description = _("creator group")

    def list_audio(self, obj):
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
                <audio class="minimal-audio-player"><source src="{obj.audio.url}" type="audio/mpeg"></audio>
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
        for value, display in Static.check_status_choices:
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

    list_audio.short_description = _("audio")

    def list_image(self, obj):
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

    def _generate_word_image_container(self, obj):
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
        for value, display in Static.check_status_choices:
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

    def _generate_unit_word_images(self, obj):
        """
        Generate HTML for the unit-specific image containers.

        Args:
            obj: The word object

        Returns:
            str: HTML markup for all unit-specific image containers
        """
        unit_word_images = ""

        for relation in obj.unit_word_relations.all():
            unit_word_images += self._generate_unit_word_image(relation)

        return unit_word_images

    def _generate_unit_word_image(self, relation):
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
        for value, display in Static.check_status_choices:
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

    list_image.short_description = _("Image")

    def singular_article_display(self, obj):
        """
        Format the singular article for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the singular article
        """
        return obj.get_singular_article_display()

    singular_article_display.short_description = _("singular article")

    def creation_date_display(self, obj):
        """
        Format the creation date for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            date: The date portion of the creation_date timestamp
        """
        return obj.creation_date.date()

    creation_date_display.short_description = _("creation date")

    def audio_check_status_display(self, obj):
        """
        Format the audio check status for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the audio check status
        """
        return obj.get_audio_check_status_display()

    audio_check_status_display.short_description = _("audio check status")
    audio_check_status_display.admin_order_field = "audio_check_status"

    def image_check_status_display(self, obj):
        """
        Format the image check status for display in the admin list view.

        Args:
            obj: The word object

        Returns:
            str: The display value of the image check status
        """
        return obj.get_image_check_status_display()

    image_check_status_display.short_description = _("image check status")
    image_check_status_display.admin_order_field = "image_check_status"
