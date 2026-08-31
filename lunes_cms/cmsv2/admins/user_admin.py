from __future__ import absolute_import, annotations, unicode_literals

from typing import Any

from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    UserChangeForm,
)
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models.review import Review


class LunesAdminAuthenticationForm(AdminAuthenticationForm):
    """
    Admin login form that reports a missing staff status with a message of its
    own, and wrong credentials with the plain wording that makes no mention of
    staff accounts.
    """

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": AuthenticationForm.error_messages["invalid_login"],
        "no_staff": _(
            "Your account is not allowed to use the Lunes administration. "
            "Please ask an administrator to activate staff status for your account."
        ),
    }

    def confirm_login_allowed(self, user: User) -> None:
        """
        Allow active accounts that hold staff status to log in.
        """
        AuthenticationForm.confirm_login_allowed(self, user)
        if not user.is_staff:
            raise ValidationError(self.error_messages["no_staff"], code="no_staff")


class LunesUserCreationForm(AdminUserCreationForm):
    """
    User creation form that requires an email address and grants staff status
    by default.
    """

    class Meta(AdminUserCreationForm.Meta):
        """
        Meta class of the user creation form
        """

        model = User
        fields = ("username", "email", "is_staff")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["is_staff"].initial = True


class LunesUserChangeForm(UserChangeForm):
    """
    User change form that requires an email address.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True


class UserReviewInline(admin.TabularInline):
    """
    Inline admin for Review on the User change page.
    """

    model = Review
    fk_name = "reviewer"
    extra = 0
    fields = ["word", "assigned_by", "assigned_at"]
    readonly_fields = ["assigned_by", "assigned_at"]
    autocomplete_fields = ["word"]
    verbose_name = _("assigned word")
    verbose_name_plural = _("assigned words")

    def has_add_permission(self, request: HttpRequest, obj: User | None = None) -> bool:
        return request.user.is_superuser

    def has_change_permission(
        self, request: HttpRequest, obj: User | None = None
    ) -> bool:
        return request.user.is_superuser

    def has_delete_permission(
        self, request: HttpRequest, obj: User | None = None
    ) -> bool:
        return request.user.is_superuser


class LunesUserAdmin(DjangoUserAdmin):
    """
    User admin extended with a Review inline so admins can grant
    per-word review access to individual users.
    """

    add_form = LunesUserCreationForm
    form = LunesUserChangeForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "is_staff",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    inlines = [*DjangoUserAdmin.inlines, UserReviewInline]

    def save_formset(
        self,
        request: HttpRequest,
        form: ModelForm[Any],
        formset: BaseModelFormSet,
        change: bool,
    ) -> None:
        if formset.model is Review:
            if not request.user.is_authenticated:
                raise PermissionDenied
            instances = formset.save(commit=False)
            for obj in formset.deleted_objects:
                obj.delete()
            for instance in instances:
                if instance.assigned_by_id is None:
                    instance.assigned_by = request.user
                instance.save()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)
