from __future__ import absolute_import, annotations, unicode_literals

from datetime import date

from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.base import BaseAdmin
from lunes_cms.cmsv2.admins.word_admin_asset_widgets import WordAdminAssetWidgetsMixin
from lunes_cms.cmsv2.admins.word_admin_list_renderers import (
    WordAdminListRenderersMixin,
)
from lunes_cms.cmsv2.admins.word_filters import (
    HasCompleteExampleSentenceFilter,
    HasImageFilter,
    MigratedFilter,
    UnitOrJobDropdownFilter,
)
from lunes_cms.cmsv2.admins.word_inlines import AlternativeWordInline, UnitInline
from lunes_cms.cmsv2.models import Word


class WordAdmin(BaseAdmin, WordAdminAssetWidgetsMixin, WordAdminListRenderersMixin):
    """
    Admin interface for the Word model.

    This admin class provides a comprehensive interface for managing words,
    including their attributes, audio files, images, and relationships with units.
    It includes custom display methods for showing and managing assets.
    """

    fieldsets = (
        (
            _("Word Information"),
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
            _("Pronunciation"),
            {"fields": ("pronunciation",)},
        ),
        (
            _("Audio"),
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
            _("Image"),
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
            _("Example Sentence"),
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
        "list_example_sentence",
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
            "js/example_sentence_check_status_update.js",
            "js/example_sentence_edit.js",
            "js/generate_example_sentence.js",
            "js/inline_regenerate.js",
            "js/alternative_word_actions.js",
        ]
        css = {"all": ["css/asset_manager.css", "css/audio_player.css"]}

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
