"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""

from __future__ import absolute_import, unicode_literals

from typing import Any

from django.contrib import admin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from .admins import (
    AreaAdmin,
    FeedbackAdmin,
    JobAdmin,
    LunesGroupAdmin,
    LunesUserAdmin,
    NotificationAdmin,
    ReviewAdmin,
    UnitAdmin,
    UnitWordRelationAdmin,
    WordAdmin,
)
from .models import (
    Area,
    Feedback,
    Job,
    Notification,
    Review,
    Unit,
    UnitWordRelation,
    Word,
)
from .models.static import is_only_reviewer


# pylint: disable=unused-argument
def has_permission(self: admin.AdminSite, request: HttpRequest) -> bool:
    """
    Return True if the given request may use the admin site.

    :param self: A handle to the :class:`admin.AdminSite`
    :param request: current user request

    :return: whether the requesting user holds an active account
    """
    return request.user.is_active


admin.AdminSite.has_permission = has_permission  # type: ignore[method-assign]

_admin_index = admin.AdminSite.index


def index(
    self: admin.AdminSite,
    request: HttpRequest,
    extra_context: dict[str, Any] | None = None,
) -> HttpResponse:
    """
    Show the admin dashboard, except to users who may only review: they are
    sent to their review view instead, e.g. right after logging in.

    :param self: A handle to the :class:`admin.AdminSite`
    :param request: current user request
    :param extra_context: additional context for the template of the dashboard

    :return: the dashboard or the redirect to the review view
    """
    if is_only_reviewer(request.user):
        return redirect("expert_access:index")
    return _admin_index(self, request, extra_context)


admin.AdminSite.index = index  # type: ignore[method-assign, assignment]

admin.site.register(Area, AreaAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(UnitWordRelation, UnitWordRelationAdmin)
admin.site.register(Word, WordAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.unregister(Group)
admin.site.register(Group, LunesGroupAdmin)
admin.site.unregister(User)
admin.site.register(User, LunesUserAdmin)
admin.site.login_form = AuthenticationForm
