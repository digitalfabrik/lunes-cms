from django.contrib import admin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .models import SessionDurationReport


@admin.register(SessionDurationReport)
class SessionDurationReportAdmin(admin.ModelAdmin):
    """
    Admin entry for the ``SessionDurationReport`` proxy model. The model is
    never browsed as rows — the changelist redirects to the sessions report
    page, so the sidebar entry behaves like a plain deep link.
    """

    def changelist_view(
        self, request: HttpRequest, extra_context: dict | None = None
    ) -> HttpResponse:
        return HttpResponseRedirect(reverse("analytics_admin:sessions_report"))

    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_superuser

    def has_view_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_superuser

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
