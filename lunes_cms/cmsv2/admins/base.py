from __future__ import annotations

from typing import Any, TYPE_CHECKING

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest

if TYPE_CHECKING:
    # Only used in the type hint below. Importing it for real would make
    # Sphinx try to document the abstract Model class itself, which crashes
    # (it has no `_meta`, unlike its concrete subclasses).
    from django.db.models import Model


class BaseAdmin(admin.ModelAdmin):
    """
    Base admin class that automatically sets the created_by field based on the user's group.

    This class extends the ModelAdmin class and overrides the save_model method
    to automatically set the created_by field to the user's first group and
    set creator_is_admin based on whether the user is a superuser.
    """

    def save_model(
        self,
        request: HttpRequest,
        obj: Any,
        form: ModelForm[Model],
        change: bool,
    ) -> None:
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0]
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()
