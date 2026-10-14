from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.models import Permission
from django.db.models import ManyToManyField
from django.forms import ModelMultipleChoiceField
from django.http import HttpRequest

CMS_VERSION_BY_APP_LABEL = {"cms": "v1", "cmsv2": "v2"}


def permission_label(permission: Permission) -> str:
    """
    Label a permission with the CMS version its model belongs to.

    :param permission: The permission to label
    :return: The permission name, prefixed with ``(v1)`` or ``(v2)`` for the
        models of the legacy and the current CMS
    """
    version = CMS_VERSION_BY_APP_LABEL.get(permission.content_type.app_label)
    if version is None:
        return str(permission)
    return f"({version}) {permission}"


class PermissionChoiceField(ModelMultipleChoiceField):
    """
    Permission choice field that labels each permission with its CMS version.
    """

    def label_from_instance(self, obj: Permission) -> str:
        return permission_label(obj)


class PermissionLabelMixin(admin.ModelAdmin):
    """
    Admin mixin that marks which CMS version each permission belongs to.
    """

    def formfield_for_manytomany(
        self,
        db_field: ManyToManyField[Any, Any],
        request: HttpRequest | None = None,
        **kwargs: Any,
    ) -> ModelMultipleChoiceField | None:
        if db_field.remote_field.model is Permission:
            kwargs["form_class"] = PermissionChoiceField
        return super().formfield_for_manytomany(
            db_field, request, **kwargs  # type: ignore[arg-type]
        )


class LunesGroupAdmin(PermissionLabelMixin, DjangoGroupAdmin):
    """
    Group admin whose permission list shows the CMS version of each permission.
    """
