"""
Register models for Django's CRUD back end
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin
from django.utils.translation import ugettext as _

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


class AdminSite(admin.AdminSite):
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
        # a.sort(key=lambda x: b.index(x[0]))
        # Sort the apps alphabetically.
        app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())

        # Sort the models alphabetically within each app.
        for app in app_list:
            app['models'].sort(key=lambda x: ordering[x['name']])

        return app_list


adminsite = AdminSite()
admin.site = adminsite
admin.sites.site = adminsite

admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
