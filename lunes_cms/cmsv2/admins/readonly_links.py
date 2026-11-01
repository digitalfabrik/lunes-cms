from __future__ import annotations

from typing import Any, Iterator

from django.contrib.admin.helpers import (
    AdminField,
    AdminForm,
    AdminReadonlyField,
    Fieldline,
    Fieldset,
)
from django.http import HttpRequest


class PermittedReadonlyField(AdminReadonlyField):
    """
    A read-only field that only links to related objects the user may view.

    Django links the related object of a read-only foreign key without checking
    any permission, so users who may not view it would run into a 403 page.
    """

    def __init__(self, *args: Any, request: HttpRequest, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request = request

    def get_admin_url(self, remote_field: Any, remote_obj: Any) -> str:
        # Only the admin itself renders these fields, always handing itself over.
        assert self.model_admin is not None
        site = self.model_admin.admin_site
        model = remote_field.model
        if site.is_registered(model) and site.get_model_admin(
            model
        ).has_view_permission(self.request, remote_obj):
            return super().get_admin_url(remote_field, remote_obj)
        return str(remote_obj)


class PermittedFieldline(Fieldline):
    """
    A line of a fieldset that renders :class:`PermittedReadonlyField`.
    """

    def __init__(self, *args: Any, request: HttpRequest, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request = request

    def __iter__(self) -> Iterator[AdminField | AdminReadonlyField]:
        for index, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield PermittedReadonlyField(
                    self.form,
                    field,
                    is_first=index == 0,
                    model_admin=self.model_admin,
                    request=self.request,
                )
            else:
                yield AdminField(self.form, field, is_first=index == 0)


class PermittedFieldset(Fieldset):
    """
    A fieldset that renders :class:`PermittedFieldline`.
    """

    def __init__(self, *args: Any, request: HttpRequest, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.request = request

    def __iter__(self) -> Iterator[Fieldline]:
        for field in self.fields:  # type: ignore[attr-defined]
            yield PermittedFieldline(
                self.form,
                field,
                self.readonly_fields,
                model_admin=self.model_admin,
                request=self.request,
            )


class PermittedAdminForm(AdminForm):
    """
    An admin form that renders :class:`PermittedFieldset`.

    The change view builds the :class:`~django.contrib.admin.helpers.AdminForm`
    itself and offers no hook to replace it, so this one takes over an
    existing one, see :meth:`.base.BaseAdmin.render_change_form`.
    """

    # pylint: disable=super-init-not-called
    def __init__(self, admin_form: AdminForm, request: HttpRequest) -> None:
        self.__dict__.update(vars(admin_form))
        self.request = request

    def __iter__(self) -> Iterator[Fieldset]:
        for name, options in self.fieldsets:
            yield PermittedFieldset(
                self.form,
                name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                request=self.request,
                **options,
            )
