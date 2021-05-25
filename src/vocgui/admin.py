"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from image_cropping import ImageCroppingMixin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.utils.module_loading import import_module
from ordered_model.admin import OrderedModelAdmin

from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage
from .list_filter import (
    DisciplineListFilter,
    DocumentTrainingSetListFilter,
    DocumentDisciplineListFilter,
)
from .forms import TrainingSetForm


class DisciplineAdmin(OrderedModelAdmin):
    """
    Admin Interface to for the Discipline module.
    Inheriting from `admin.ModelAdmin`.
    """

    search_fields = ["title"]
    actions = ['delete_selected', 'make_released', 'make_unreleased']

    @admin.action(description=_("Release selected disciplines"))
    def make_released(self, request, queryset):
        queryset.update(released = True)

    @admin.action(description=_("Unrelease selected disciplines"))
    def make_unreleased(self, request, queryset):
        queryset.update(released = False)

    def get_action_choices(self, request):
        choices = super(DisciplineAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices
    
    list_display = ("title", "released", "move_up_down_links")
    list_per_page = 25


class TrainingSetAdmin(OrderedModelAdmin):
    """
    Admin Interface to for the TrainigSet module.
    Inheriting from `admin.ModelAdmin`.
    """

    search_fields = ["title"]
    form = TrainingSetForm
    list_display = ("title", "released", "move_up_down_links")
    list_filter = (DisciplineListFilter,)
    actions = ['make_released', 'make_unreleased']
    list_per_page = 25

    @admin.action(description=_("Release selected training sets"))
    def make_released(self, request, queryset):
        queryset.update(released = True)     

    @admin.action(description=_("Unrelease selected training sets"))
    def make_unreleased(self, request, queryset):
        queryset.update(released = False)

    def get_action_choices(self, request):
        choices = super(TrainingSetAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

class AlternativeWordAdmin(admin.StackedInline):
    """
    Admin Interface to for the AlternativeWord module.
    Inheriting from `admin.StackedInline`.
    """

    model = AlternativeWord
    search_fields = ["alt_word"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0


class DocumentImageAdmin(admin.StackedInline):
    """
    Admin Interface to for the DocumentImage module.
    Inheriting from `admin.StackedInline`.
    """

    model = DocumentImage
    search_fields = ["name"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0


class DocumentAdmin(admin.ModelAdmin):
    """
    Admin Interface to for the Document module.
    Inheriting from `admin.ModelAdmin`.
    """

    search_fields = ["word"]
    inlines = [DocumentImageAdmin, AlternativeWordAdmin]
    ordering = ["word", "creation_date"]
    list_display = ("word", "word_type", "article", "creation_date")
    list_filter = (
        DocumentTrainingSetListFilter,
        DocumentDisciplineListFilter,
    )
    list_per_page = 25

    def get_action_choices(self, request):
        choices = super(DocumentAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices


def get_app_list(self, request):
    """
    Function that returns a sorted list of all the installed apps that have been
    registered in this site.

    :param self: A handle to the :class:`admin.AdminSite`
    :type self: class: `admin.AdminSite`
    :param request: Current HTTP request
    :type request: HTTP request

    :return: list of app dictionaries (e.g. containing models)
    :rtype: list
    """
    ordering = {
        _("disciplines").capitalize(): 1,
        _("training sets").capitalize(): 2,
        _("vocabulary").capitalize(): 3,
    }
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
