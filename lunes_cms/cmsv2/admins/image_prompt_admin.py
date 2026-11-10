from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from ..models import ImagePrompt
from ..models.image_prompt import LOCKED_FIELDS

if TYPE_CHECKING:
    from django.contrib.admin.options import _FieldsetSpec, ActionLocation
    from django.db.models import QuerySet
    from django.http import HttpRequest
    from django.utils.safestring import SafeString

#: Example of an optional part, shown in the help of the prompt fields. Kept
#: out of the translated text, since its template tags would be read as
#: format placeholders.
OPTIONAL_PART_EXAMPLE = "{% if job %} Beruflicher Kontext: {{ job }}.{% endif %}"


def _prompt_description(prompt: ImagePrompt | None) -> SafeString:
    """
    The explanation above the prompt fields.
    """
    description = format_html(
        "{}<br><code>{}</code><br>{}",
        _(
            "Prompts use the Django template language. Available variables: "
            "word, job, unit and additional_info. All but word can be empty, so "
            "put the parts using them in an if block, for example:"
        ),
        OPTIONAL_PART_EXAMPLE,
        _(
            "The ban on text in the image and the instruction for the AI label "
            "are appended automatically. They are in German, so write prompts "
            "in German as well."
        ),
    )
    if prompt is not None and prompt.is_used:
        description = format_html(
            "{}<br><strong>{}</strong>",
            description,
            _(
                "This prompt has already been used to generate images, so its "
                "text can't be changed any more. Copy it in the list to make "
                "changes."
            ),
        )
    return description


def _prompt_fields(prompt: ImagePrompt | None) -> tuple[str, ...]:
    """
    The fields of the prompt section.

    A used prompt is read-only, so only the text it is rendered from is
    shown. Otherwise all fields are rendered and ``image_prompt_fields.ts``
    shows the ones matching the "supports show people" checkbox.
    """
    if prompt is not None and prompt.is_used:
        return ("supports_show_people", *prompt.template_fields())
    return LOCKED_FIELDS


class ImagePromptAdmin(admin.ModelAdmin):
    """
    Admin interface for the image generation prompts (#1143), for superusers
    only.

    Used prompts and the default prompt can't be deleted, and the text of a
    used prompt can't be changed; the copy action makes an editable duplicate.
    """

    list_display = [
        "name",
        "supports_show_people",
        "is_default",
        "is_active",
        "used_at",
    ]
    list_filter = ["is_active", "supports_show_people"]
    search_fields = ["name"]
    actions = ["copy_prompts"]

    class Media:
        """
        Show only the prompt fields matching "supports show people".
        """

        js = ("js/image_prompt_fields.js",)

    def get_fieldsets(
        self, request: HttpRequest, obj: ImagePrompt | None = None
    ) -> _FieldsetSpec:
        return [
            (None, {"fields": ["name", "is_default", "is_active", "used_at"]}),
            (
                _("Prompt"),
                {
                    "fields": _prompt_fields(obj),
                    "description": _prompt_description(obj),
                },
            ),
        ]

    def get_readonly_fields(
        self, request: HttpRequest, obj: ImagePrompt | None = None
    ) -> list[str]:
        if obj is not None and obj.is_used:
            return ["used_at", *LOCKED_FIELDS]
        return ["used_at"]

    def get_actions(  # pylint: disable=unused-argument
        self, request: HttpRequest, action_location: ActionLocation | None = None
    ) -> dict[str, Any]:
        """
        Drop the bulk delete, which doesn't check the prompts one by one.
        """
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.action(description=_("Copy selected prompts"))
    def copy_prompts(
        self, request: HttpRequest, queryset: QuerySet[ImagePrompt]
    ) -> HttpResponseRedirect | None:
        """
        Create an editable copy of every selected prompt. A single copy is
        opened right away.
        """
        copies = [prompt.copy() for prompt in queryset]
        self.message_user(
            request,
            ngettext(
                "%(count)d prompt was copied.",
                "%(count)d prompts were copied.",
                len(copies),
            )
            % {"count": len(copies)},
            messages.SUCCESS,
        )
        if len(copies) == 1:
            return HttpResponseRedirect(
                reverse("admin:cmsv2_imageprompt_change", args=[copies[0].pk])
            )
        return None

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: ImagePrompt | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: ImagePrompt | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: ImagePrompt | None = None
    ) -> bool:
        if not request.user.is_superuser:
            return False
        return obj is None or not (obj.is_default or obj.is_used)
