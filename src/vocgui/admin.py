"""
Register models for Django's CRUD back end
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.utils.module_loading import import_module

from .list_filter import DisciplineListFilter, DocumentTrainingSetListFilter, DocumentDisciplineListFilter
import nested_admin

from .forms import TrainingSetForm

"""
Specify autocomplete_fields, search_fields and nested modules
"""


class DisciplineAdmin(admin.ModelAdmin):
    search_fields = ['title']
    ordering = ['title']


class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['discipline']
    form = TrainingSetForm
    ordering = ['title', 'discipline__title']
    list_filter = (DisciplineListFilter,)


class AlternativeWordAdmin(nested_admin.NestedStackedInline):
    model = AlternativeWord
    search_fields = ['alt_word']
    autocomplete_fields = ['document']
    insert_after = 'autocomplete_fields'
    extra = 0


class DocumentImageAdmin(nested_admin.NestedStackedInline):
    model = DocumentImage
    search_fields = ['name']
    autocomplete_fields = ['document']
    insert_after = 'autocomplete_fields'
    extra = 0


class DocumentAdmin(nested_admin.NestedModelAdmin):
    search_fields = ['word']
    inlines = [DocumentImageAdmin, AlternativeWordAdmin]
    ordering = ['word']
    list_filter = (DocumentTrainingSetListFilter, DocumentDisciplineListFilter,)


#class AdminSite(admin.AdminSite):
def get_app_list(self, request):
    """
    Return a sorted list of all the installed apps that have been
    registered in this site.
    """
    ordering = {
        _("disciplines").capitalize(): 1,
        _("training sets").capitalize(): 2,
        _("vocabulary").capitalize(): 3,
    }
    app_dict = self._build_app_dict(request)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())

    # Sort the respective modules according the defined order
    for app in app_list:
        try:
            app['models'].sort(key=lambda x: ordering[x['name']])
        except KeyError:
            pass
    return app_list


admin.AdminSite.get_app_list = get_app_list 
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
