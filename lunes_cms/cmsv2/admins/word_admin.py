from __future__ import absolute_import, annotations, unicode_literals

from datetime import date
from typing import Any, TYPE_CHECKING

from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.forms import ModelForm
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe, SafeString
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.admins.area_content_admin import AreaContentAdmin
from lunes_cms.cmsv2.admins.area_filters import AreaListFilter
from lunes_cms.cmsv2.admins.word_admin_asset_widgets import WordAdminAssetWidgetsMixin
from lunes_cms.cmsv2.admins.word_admin_list_renderers import (
    WordAdminListRenderersMixin,
)
from lunes_cms.cmsv2.admins.word_filters import (
    HasCompleteExampleSentenceFilter,
    HasImageFilter,
    ImageSourceFilter,
    JobDropdownFilter,
    MigratedFilter,
    UnitDropdownFilter,
)
from lunes_cms.cmsv2.admins.word_inlines import (
    AlternativeWordInline,
    format_html_lazy,
    UnitInline,
)
from lunes_cms.cmsv2.areas import (
    scope_words,
    validate_word_area,
    visible_unit_word_relations,
    visible_units,
)
from lunes_cms.cmsv2.models import Word
from lunes_cms.cmsv2.models.area import Area
from lunes_cms.cmsv2.models.static import image_upload_warning_html_lazy
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.notifications import notify_words_added
from lunes_cms.cmsv2.reviews import (
    assign_reviews,
    available_units_per_word,
    may_assign_reviews,
)

if TYPE_CHECKING:
    from django.utils.functional import _StrOrPromise


class WordAdminForm(ModelForm):
    """
    Form for the Word model that keeps a word inside a single area.
    """

    class Meta:
        """
        Meta class of the word form
        """

        model = Word
        fields = "__all__"
        help_texts = {"image": image_upload_warning_html_lazy()}

    def clean_area(self) -> Area | None:
        """
        Reject moving a word that is used in units of its current area.

        A word can only be used in units of its own area, so it has to be
        moved together with its units, see
        :func:`~lunes_cms.cmsv2.areas.validate_word_area`.
        """
        area = self.cleaned_data["area"]
        if area != self.instance.area:
            validate_word_area(self.instance, area)
        return area


class WordAdmin(
    AreaContentAdmin, WordAdminAssetWidgetsMixin, WordAdminListRenderersMixin
):
    """
    Admin interface for the Word model.

    This admin class provides a comprehensive interface for managing words,
    including their attributes, audio files, images, and relationships with units.
    It includes custom display methods for showing and managing assets.
    """

    form = WordAdminForm
    fieldsets = (
        (
            format_html_lazy("<h2>{}</h2>", _("Word Information")),
            {
                "fields": (
                    "word_type",
                    "grammatical_gender",
                    "singular_article",
                    "word",
                    "plural_article",
                    "plural",
                    "area",
                    "migrated_status",
                )
            },
        ),
        (
            format_html_lazy("<h2>{}</h2>", _("Pronunciation")),
            {"fields": ("pronunciation",)},
        ),
        (
            format_html_lazy("<h2>{}</h2>", _("Audio")),
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
            format_html_lazy("<h2>{}</h2>", _("Image")),
            {
                "fields": (
                    "image",
                    "image_check_status",
                    "image_source",
                    "image_generate",
                    "image_tag",
                )
            },
        ),
        (
            format_html_lazy("<h2>{}</h2>", _("Example Sentence")),
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
        "image_source",
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
        "area",
        "creator_group",
        "created_by_user",
        "creation_date_display",
    )
    list_filter = [
        "word_type",
        "audio_check_status",
        "image_check_status",
        HasImageFilter,
        ImageSourceFilter,
        ("area", AreaListFilter),
        JobDropdownFilter,
        UnitDropdownFilter,
        HasCompleteExampleSentenceFilter,
        MigratedFilter,
        "created_by",
    ]
    list_select_related = ["area", "created_by", "created_by_user"]
    list_per_page = 25
    actions = ["assign_to_user"]

    class Media:
        """
        Media class for including JavaScript and CSS files in the admin interface.

        This class specifies the static files needed for the word admin interface,
        including scripts for asset management, audio playback, and status updates.
        """

        js = [
            "js/csrf.js",
            "js/word_image_asset_config.js",
            "js/unitword_image_asset_config.js",
            "js/asset_manager.js",
            "js/word_audio_asset_config.js",
            "js/word_example_sentence_audio_asset_config.js",
            "js/audio_asset_manager.js",
            "js/audio_player.js",
            "js/audio_check_status_update.js",
            "js/image_check_status_update.js",
            "js/example_sentence_check_status_update.js",
            "js/example_sentence_edit.js",
            "js/example_sentence_audio_regenerate.js",
            "js/generate_example_sentence.js",
            "js/inline_regenerate.js",
            "js/image_prompt_preview.js",
            "js/alternative_word_actions.js",
        ]
        css = {
            "all": [
                "css/asset_manager.css",
                "css/audio_player.css",
                "css/image_prompt_info.css",
            ]
        }

    def get_queryset(self, request: HttpRequest) -> QuerySet[Word]:
        """
        Restrict the words to the area of the user and prefetch the units
        and jobs the "area" column derives from (#1007).
        """
        return scope_words(
            super().get_queryset(request).prefetch_related("units__jobs__area"),
            request.user,
        )

    def save_formset(
        self,
        request: HttpRequest,
        form: ModelForm[Any],
        formset: BaseInlineFormSet,
        change: bool,
    ) -> None:
        """Tell the experts of the units about this word being added to them"""
        super().save_formset(request, form, formset, change)
        if formset.model is UnitWordRelation:
            notify_words_added(formset.new_objects, added_by=request.user)

    def area(self, obj: Word) -> Area | None:
        """
        The area of the word, derived from the units it is linked to.

        Args:
            obj: The word object

        Returns:
            Area or None: The area of the word, or None for main app content
        """
        return obj.area

    area.short_description = _("area")  # type: ignore[attr-defined]

    def has_assign_permission(self, request: HttpRequest) -> bool:
        """Whether the user may assign words to other users for review"""
        return may_assign_reviews(request.user)

    @admin.action(
        description=_("Assign selected words to user"), permissions=["assign"]
    )
    def assign_to_user(
        self, request: HttpRequest, queryset: QuerySet[Word]
    ) -> HttpResponse | None:
        """
        Bulk-create Reviews of the selected words for a chosen user.
        Only the words, units and unit word relations visible to the user are considered.

        First, the user is redirected to a page to selected unit for the selected words, such
        that unit word relations can be assigned for review.
        """

        def send_message(msg: _StrOrPromise, num_words_without_unit: int) -> None:
            """Messages the user that the assignment was successful."""
            self.message_user(request, msg)

            if num_words_without_unit > 0:
                self.message_user(
                    request,
                    _(
                        "%(count)d word(s) were skipped, because they do not belong to any unit."
                    )
                    % {"count": num_words_without_unit},
                    messages.WARNING,
                )

        queryset = scope_words(queryset, request.user)
        words, words_without_unit = available_units_per_word(
            queryset, limit_units_to=visible_units(request.user)
        )

        if "apply" not in request.POST:
            return TemplateResponse(
                request,
                "admin/cmsv2/assign_words_to_user.html",
                {
                    **self.admin_site.each_context(request),
                    "words": words,
                    "words_without_unit": words_without_unit,
                    "users": User.objects.order_by("username"),
                    "action": "assign_to_user",
                    "selected_action": queryset.values_list("pk", flat=True),
                    "title": _("Assign selected words to user"),
                },
            )

        user = get_object_or_404(User, pk=request.POST["user"])
        selected_relation_ids = [
            request.POST.get(
                f"unit_word_{word.pk}", word.available_review_relations[0].pk
            )
            for word in words
        ]
        selected_relations = visible_unit_word_relations(request.user).filter(
            pk__in=selected_relation_ids
        )

        message = assign_reviews(
            selected_relations, reviewer=user, assigner=request.user
        )
        send_message(message, len(words_without_unit))
        return None

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
