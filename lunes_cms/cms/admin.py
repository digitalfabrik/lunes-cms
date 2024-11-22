"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .admins import (
    DisciplineAdmin,
    DocumentAdmin,
    FeedbackAdmin,
    GroupAPIKeyAdmin,
    SponsorAdmin,
    TrainingSetAdmin,
)
from .models import Discipline, Document, Feedback, GroupAPIKey, Sponsor, TrainingSet


def get_app_list(self, request):
    """
    Function that returns a sorted list of all the installed apps that have been
    registered in this site.

    :param self: A handle to the :class:`admin.AdminSite`
    :type self: class: `admin.AdminSite`
    :param request: current user request
    :type request: django.http.request

    :return: list of app dictionaries (e.g. containing models)
    :rtype: list
    """
    ordering = {
        _("disciplines").capitalize(): 1,
        _("training sets").capitalize(): 2,
        _("vocabulary").capitalize(): 3,
        _("api keys").capitalize(): 4,
        _("feedback").capitalize(): 5,
    }

    # pylint: disable=protected-access
    app_dict = self._build_app_dict(request)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())

    # Sort the respective modules according the defined order
    for app in app_list:
        try:
            app["models"].sort(key=lambda x: ordering[x["name"]])
        except KeyError:
            pass
    return app_list


admin.AdminSite.get_app_list = get_app_list
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(GroupAPIKey, GroupAPIKeyAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(Sponsor, SponsorAdmin)
