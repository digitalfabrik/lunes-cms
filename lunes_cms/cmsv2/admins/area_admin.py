from __future__ import absolute_import, annotations, unicode_literals

from datetime import date
from typing import Any

from django.contrib import admin
from django.db.models import Count, Field, Q, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ..models import Area, AreaAccessToken, AreaCode


class AreaCodeInline(admin.TabularInline):
    """
    Inline admin for the codes of an area.

    The codes are edited together with their area, because they only make sense
    as part of it and are managed by the same people. A code is always typed in
    by the person who hands it out, so the empty row carries no suggestion.
    """

    model = AreaCode
    extra = 1
    fields = ["code", "created_at"]
    readonly_fields = ["created_at"]
    verbose_name = _("code")
    verbose_name_plural = _("codes")


class AreaAccessTokenInline(admin.TabularInline):
    """
    Inline admin for the access tokens that were handed out for an area.

    Tokens are only ever created by the API when a client redeems a code, so
    the only thing to do here is to look at them and to revoke them.
    """

    model = AreaAccessToken
    extra = 0
    # Tokens are only ever created by the API, and the Jazzmin inline template
    # renders its "add another" row regardless of ``has_add_permission``, so
    # the row is taken away by the formset itself.
    max_num = 0
    can_delete = False
    fields = [
        "token_prefix",
        "code",
        "installation_id",
        "created_at",
        "last_used_at",
        "revoked",
    ]
    readonly_fields = [
        "token_prefix",
        "code",
        "installation_id",
        "created_at",
        "last_used_at",
    ]
    verbose_name = _("access token")
    verbose_name_plural = _("access tokens")

    def has_add_permission(self, request: HttpRequest, obj: Area | None = None) -> bool:
        return False


class AreaAdmin(admin.ModelAdmin):
    """
    Admin interface for the Area model.

    Areas are created and assigned by superusers only, because assigning an
    area decides who may see and change the content below it.
    """

    fields = [
        "name",
        "logo",
        "logo_tag",
        "primary_color",
        "secondary_color",
        "additional_information",
        "additional_information_url",
        "admins",
    ]
    readonly_fields = ["logo_tag"]
    filter_horizontal = ["admins"]
    inlines = [AreaCodeInline, AreaAccessTokenInline]
    search_fields = ["name"]
    ordering = ["name"]
    list_display = [
        "name",
        "administrators",
        "number_jobs",
        "number_codes",
        "number_tokens",
        "created_at_date",
    ]
    list_display_links = ["name"]
    list_per_page = 25

    def formfield_for_dbfield(
        self, db_field: "Field[Any, Any]", request: HttpRequest, **kwargs: Any
    ) -> Any:
        """Stretch the URL field to the full width so a long link is readable at a glance."""
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "additional_information_url" and formfield is not None:
            formfield.widget.attrs["style"] = "width: 100%"
        return formfield

    def get_queryset(self, request: HttpRequest) -> QuerySet[Area]:
        """Annotate the job and code counts and prefetch the administrators."""
        return (
            super()
            .get_queryset(request)
            .annotate(job_count=Count("jobs", distinct=True))
            .annotate(code_count=Count("codes", distinct=True))
            .annotate(
                token_count=Count(
                    "access_tokens",
                    filter=Q(access_tokens__revoked=False),
                    distinct=True,
                )
            )
            .prefetch_related("admins")
        )

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: Area | None = None
    ) -> bool:
        return request.user.is_superuser

    def administrators(self, obj: Area) -> str:
        """
        Get a comma-separated list of the administrators of this area.

        Args:
            obj: The area object

        Returns:
            str: A comma-separated list of user names
        """
        return ", ".join(user.get_username() for user in obj.admins.all())

    administrators.short_description = _("administrators")  # type: ignore[attr-defined]

    def number_jobs(self, obj: Area) -> int:
        """
        Get the number of jobs that belong to this area.

        Args:
            obj: The area object

        Returns:
            int: The number of jobs of the area
        """
        return obj.job_count  # type: ignore[attr-defined]

    number_jobs.short_description = _("jobs")  # type: ignore[attr-defined]

    def number_codes(self, obj: Area) -> int:
        """
        Get the number of codes that belong to this area.

        Args:
            obj: The area object

        Returns:
            int: The number of codes of the area
        """
        return obj.code_count  # type: ignore[attr-defined]

    number_codes.short_description = _("codes")  # type: ignore[attr-defined]

    def number_tokens(self, obj: Area) -> int:
        """
        Get the number of clients that currently have access to this area.

        Args:
            obj: The area object

        Returns:
            int: The number of access tokens of the area that are not revoked
        """
        return obj.token_count  # type: ignore[attr-defined]

    number_tokens.short_description = _("clients")  # type: ignore[attr-defined]

    def created_at_date(self, obj: Area) -> date:
        """
        Format the created_at timestamp as a date.

        Args:
            obj: The area object

        Returns:
            date: The date portion of the created_at timestamp
        """
        return obj.created_at.date()

    created_at_date.short_description = _("created at")  # type: ignore[attr-defined]
