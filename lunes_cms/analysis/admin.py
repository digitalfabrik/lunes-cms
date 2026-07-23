from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from ..cmsv2.services.duplicate_words import duplicate_word_group_count
from .models import DuplicatedVocabulary

_previous_get_app_list = admin.AdminSite.get_app_list


def _get_app_list(
    self: admin.AdminSite, request: HttpRequest, _app_label: str | None = None
) -> list[dict[str, Any]]:
    """
    Wraps the existing ``get_app_list`` patch (``lunes_cms/cms/admin.py``) to
    append a live duplicate count to the "Duplicated vocabulary" sidebar
    entry, e.g. "Duplicated vocabulary (3)" (#531).
    """
    # `_previous_get_app_list` (patched in `lunes_cms/cms/admin.py`) only
    # accepts `request` — it doesn't support `app_label` filtering, so this
    # wrapper doesn't either.
    app_list = _previous_get_app_list(self, request)
    count = duplicate_word_group_count()
    if count:
        for app in app_list:
            if app["app_label"] != "analysis":
                continue
            for model in app["models"]:
                if model["object_name"] == "DuplicatedVocabulary":
                    model["name"] = f"{model['name']} ({count})"
    return app_list


admin.AdminSite.get_app_list = _get_app_list  # type: ignore[method-assign,assignment]


@admin.register(DuplicatedVocabulary)
class DuplicatedVocabularyAdmin(admin.ModelAdmin):
    """
    A sidebar entry, not a real CRUD interface: clicking "Duplicated
    vocabulary" under "Analyse" redirects straight to the actual analysis
    page (``cmsv2:duplicated_vocabulary``), which owns the real behaviour
    (issue #531).
    """

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        return redirect("cmsv2:duplicated_vocabulary")

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_staff

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return request.user.is_staff

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
