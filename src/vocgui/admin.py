"""
Register models for Django's CRUD back end
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin

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
    list_filter = (DisciplineListFilter, )
    

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
    list_filter = (DocumentTrainingSetListFilter, DocumentDisciplineListFilter, )

admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
