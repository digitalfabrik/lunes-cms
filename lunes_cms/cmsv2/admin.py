"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""

from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.http import HttpRequest

from .admins import FeedbackAdmin, JobAdmin, LunesUserAdmin, UnitAdmin, WordAdmin
from .models import Feedback, Job, Unit, Word


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

admin.site.register(Job, JobAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Word, WordAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.unregister(User)
admin.site.register(User, LunesUserAdmin)
admin.site.login_form = AuthenticationForm
