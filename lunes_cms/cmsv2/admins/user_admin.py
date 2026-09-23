from __future__ import absolute_import, annotations, unicode_literals

from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.forms import BaseModelFormSet, ModelForm
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models.area import Area
from lunes_cms.cmsv2.models.review import Review


class LunesUserCreationForm(AdminUserCreationForm):
    """
    User creation form that requires an email address.
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
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    inlines = [*DjangoUserAdmin.inlines, UserReviewInline]

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
