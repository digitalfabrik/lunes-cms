from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models.review import ReviewAssignment


class UserReviewAssignmentInline(admin.TabularInline):
    """
    Inline admin for ReviewAssignment on the User change page.
    """

    model = ReviewAssignment
    fk_name = "reviewer"
    extra = 0
    fields = ["unit", "assigned_by", "assigned_at"]
    readonly_fields = ["assigned_by", "assigned_at"]
    autocomplete_fields = ["unit"]
    verbose_name = _("assigned unit")
    verbose_name_plural = _("assigned units")

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class LunesUserAdmin(DjangoUserAdmin):
    """
    User admin extended with a ReviewAssignment inline so admins can grant
    per-unit access to individual users.
    """

    inlines = [*DjangoUserAdmin.inlines, UserReviewAssignmentInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is ReviewAssignment:
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
