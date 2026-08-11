from __future__ import annotations

from typing import Any, Callable

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from ..cmsv2.services.duplicate_words import duplicate_word_group_count
from ..core.permissions import can_view_duplicates
from .models import AcceptedDuplicates, DuplicatedVocabulary

_previous_get_app_list = admin.AdminSite.get_app_list


def _get_app_list(
    self: admin.AdminSite, request: HttpRequest, _app_label: str | None = None
) -> list[dict[str, Any]]:
    """
    Wraps the existing ``get_app_list`` patch (``lunes_cms/cms/admin.py``) to
    (issue #531):

    - append a live duplicate count to the "Open duplicates" sidebar entry,
      e.g. "Open duplicates (3)"
    - point "Accepted duplicates" at its nicer-looking URL
      (``cmsv2:accepted_duplicates``) instead of Django's auto-generated
      ``.../analysis/acceptedduplicates/`` (named after the Python class,
      which can't contain a hyphen) — the changelist itself is unaffected,
      only the sidebar link changes.
    """
    # `_previous_get_app_list` (patched in `lunes_cms/cms/admin.py`) only
    # accepts `request` — it doesn't support `app_label` filtering, so this
    # wrapper doesn't either.
    app_list = _previous_get_app_list(self, request)
    count = duplicate_word_group_count()
    for app in app_list:
        if app["app_label"] != "analysis":
            continue
        for model in app["models"]:
            if count and model["object_name"] == "DuplicatedVocabulary":
                model["name"] = f"{model['name']} ({count})"
            elif model["object_name"] == "AcceptedDuplicates":
                model["admin_url"] = reverse("cmsv2:accepted_duplicates")
    return app_list


admin.AdminSite.get_app_list = _get_app_list  # type: ignore[method-assign,assignment]


@admin.register(DuplicatedVocabulary)
class DuplicatedVocabularyAdmin(admin.ModelAdmin):
    """
    A sidebar entry, not a real CRUD interface: clicking "Open duplicates"
    under "Analyse" redirects straight to the actual analysis page
    (``cmsv2:duplicated_vocabulary``), which owns the real behaviour
    (issue #531).
    """

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        return redirect("cmsv2:duplicated_vocabulary")

    def has_module_permission(self, request: HttpRequest) -> bool:
        return can_view_duplicates(request.user)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return can_view_duplicates(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(AcceptedDuplicates)
class AcceptedDuplicatesAdmin(admin.ModelAdmin):
    """
    Read-only(-ish) list of duplicate-vocabulary groups a content manager has
    explicitly accepted as intentional (issue #531). A regular Django
    changelist — not a custom page like "Open duplicates" — since there's
    nothing bespoke to show beyond the words and when it was accepted.

    Deleting an entry here is how you "undo" an acceptance: the group simply
    stops being excluded and reappears under "Open duplicates".
    """

    list_display = ("words_display", "created_at")
    # No change view exists here (has_change_permission is always False) -
    # without this, Django's default would still linkify the first column
    # to it anyway.
    list_display_links: None = None
    ordering = ("-created_at",)
    actions = ["undo_accepted_duplicates"]

    def words_display(self, obj: AcceptedDuplicates) -> str:
        """Delegates to ``str(obj)``, which already shows the group's shared word text once."""
        return str(obj)

    words_display.short_description = _("word")  # type: ignore[attr-defined]

    def has_module_permission(self, request: HttpRequest) -> bool:
        return can_view_duplicates(request.user)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return can_view_duplicates(request.user)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return can_view_duplicates(request.user)

    def get_actions(
        self, request: HttpRequest
    ) -> dict[str, tuple[Callable[..., Any], str, str] | None]:
        # Drop the default "Delete selected ..." action - `undo_accepted_duplicates`
        # below does the exact same deletion, just under a label that
        # matches what it actually means for this model (issue #531).
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.action(description=_("Undo selected accepted duplicates"))
    def undo_accepted_duplicates(
        self, request: HttpRequest, queryset: QuerySet[AcceptedDuplicates]
    ) -> None:
        """Deleting the entry is the undo: the group(s) simply stop being
        excluded and reappear under "Open duplicates" (issue #531)."""
        count = queryset.count()
        queryset.delete()
        messages.success(
            request,
            _("%(count)d accepted duplicate(s) undone.") % {"count": count},
        )
