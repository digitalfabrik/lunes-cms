from __future__ import absolute_import, annotations, unicode_literals

import smtplib
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models.area import Area
from lunes_cms.cmsv2.models.review import Review


class LunesUserCreationForm(AdminUserCreationForm):
    """
    User creation form that only asks for a username and an email address.

    The admin never picks a password: the account is created with an
    unusable password and the user sets their own through the link in the
    invitation email :meth:`LunesUserAdmin.send_mail` sends.
    """

    class Meta(AdminUserCreationForm.Meta):
        """
        Meta class of the user creation form
        """

        model = User
        fields = ("username", "email")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        for name in ("usable_password", "password1", "password2"):
            del self.fields[name]

    def validate_passwords(  # pylint: disable=unused-argument
        self, *args: Any, **kwargs: Any
    ) -> None:
        # Makes ``set_password_and_save`` call ``set_unusable_password``.
        self.cleaned_data["set_usable_password"] = False


class LunesUserChangeForm(UserChangeForm):
    """
    User change form that requires an email address and lets a superuser
    assign the areas this user administers, the same relation the area
    change page edits from the other side.
    """

    administered_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(_("areas"), False),
        label=_("administered areas"),
        help_text=_(
            "The areas this user administers. They only see the jobs, units "
            "and words of the areas they administer."
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        if self.instance.pk:
            self.fields["administered_areas"].initial = (
                self.instance.administered_areas.all()
            )

    def _save_m2m(self) -> None:
        super()._save_m2m()  # type: ignore[misc]
        self.instance.administered_areas.set(self.cleaned_data["administered_areas"])


class UserReviewInline(admin.TabularInline):
    """
    Inline admin for Review on the User change page.
    """

    model = Review
    fk_name = "reviewer"
    extra = 0
    fields = ["unit_word", "assigned_by", "assigned_at"]
    readonly_fields = ["assigned_by", "assigned_at"]
    autocomplete_fields = ["unit_word"]
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
    fieldsets = tuple(
        (
            name,
            {
                **options,
                "fields": tuple(options["fields"])
                + (("administered_areas",) if name == _("Permissions") else ()),
            },
        )
        for name, options in DjangoUserAdmin.fieldsets or ()
    )
    list_display = ("username", "email", "first_name", "last_name")
    list_filter = ("is_superuser", "is_active", "groups")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email"),
            },
        ),
    )
    inlines = [*DjangoUserAdmin.inlines, UserReviewInline]
    actions = ["resend_invitation"]

    def get_form(  # type: ignore[override]
        self, request: HttpRequest, obj: User | None = None, **kwargs: Any
    ) -> type[ModelForm[Any]]:
        """
        Only superusers assign areas, the same restriction ``AreaAdmin``
        enforces from the other side of the relation.

        The field is disabled rather than listed in ``readonly_fields``:
        Django drops a field from the form entirely once it is both in a
        fieldset and in ``readonly_fields``, even one declared directly on
        the form class, which would crash ``LunesUserChangeForm.__init__``
        looking it up. A disabled field stays part of the form — rendered,
        but ignoring whatever a crafted request submits for it in favor of
        its initial value — which is what "read-only" has to mean here.

        Disabling happens on a form *instance*, in a subclass made fresh for
        this request, never on ``form.base_fields`` directly: that dict is
        built once per form class and its field objects are shared with
        every other form built from ``LunesUserChangeForm``, so mutating one
        there would disable the field for every user of the admin, superusers
        included, from the moment the first non-superuser opened this page.
        """
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser or "administered_areas" not in form.base_fields:
            return form

        class ReadOnlyAreasForm(form):  # type: ignore[misc,valid-type]
            """``form`` with the areas field disabled for this one instance."""

            def __init__(self, *args: Any, **inner_kwargs: Any) -> None:
                super().__init__(*args, **inner_kwargs)
                self.fields["administered_areas"].disabled = True

        return ReadOnlyAreasForm

    def save_model(
        self,
        request: HttpRequest,
        obj: User,
        form: ModelForm[Any],
        change: bool,
    ) -> None:
        """
        Notify a newly created user by email once their account is saved.
        """
        super().save_model(request, obj, form, change)
        if not change and not self.send_mail(request, obj):
            messages.warning(
                request,
                gettext(
                    "The account was created, but the email with the link to "
                    "set the password could not be sent to {email}."
                ).format(email=obj.email),
            )

    @admin.action(description=_("Resend invitation email"), permissions=["change"])
    def resend_invitation(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        """
        Send the invitation email again, with a fresh link, to the selected
        users who have not set a password yet.

        Users who already have a password are skipped: for them the
        invitation text would be wrong, and they can use "forgot password"
        instead, which ignores accounts without a usable password. Users
        without an email address are skipped as well.
        """
        users = list(queryset)
        invited = [
            user for user in users if user.email and not user.has_usable_password()
        ]
        sent = sum(self.send_mail(request, user) for user in invited)
        if sent:
            messages.success(
                request,
                _("%(count)d invitation email(s) have been sent.") % {"count": sent},
            )
        if failed := len(invited) - sent:
            messages.error(
                request,
                _("%(count)d invitation email(s) could not be sent.")
                % {"count": failed},
            )
        if skipped := len(users) - len(invited):
            messages.warning(
                request,
                _(
                    "%(count)d user(s) were skipped because they already set a "
                    "password or have no email address."
                )
                % {"count": skipped},
            )

    def send_mail(self, request: HttpRequest, user: User) -> bool:
        """
        Send the account creation notification to ``user`` with a link to
        set their password, and return whether that worked.

        The link points to the regular password reset confirmation page, so
        it expires after :setting:`django:PASSWORD_RESET_TIMEOUT` and stops
        working once the password has been set. The mail goes out through
        the configured :setting:`django:EMAIL_BACKEND`.
        """
        set_password_url = request.build_absolute_uri(
            reverse(
                "password_reset_confirm",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": default_token_generator.make_token(user),
                },
            )
        )
        subject = gettext("Your Lunes CMS account has been created")
        message = gettext(
            "Hello {username},\n\n"
            "an account has been created for you in the Lunes CMS.\n"
            "Please set your password using the following link:\n\n"
            "{url}\n\n"
            "Your username is: {username}"
        ).format(username=user.get_username(), url=set_password_url)
        try:
            send_mail(subject, message, None, [user.email])
        except (smtplib.SMTPException, OSError):
            return False
        return True

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
