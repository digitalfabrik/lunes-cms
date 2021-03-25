"""
Register models for Django's CRUD back end
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin

from .list_filter import DisciplineListFilter, TrainingSetListFilter
import nested_admin

"""
Specify autocomplete_fields, search_fields and nested modules
"""


class DisciplineAdmin(admin.ModelAdmin):
    search_fields = ['title']
    ordering = ['title']


class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['discipline']
    ordering = ['discipline__title', 'title']
    list_filter = (DisciplineListFilter, )


class AlternativeWordAdmin(nested_admin.NestedStackedInline):
    model = AlternativeWord
    search_fields = ['alt_word']
    autocomplete_fields = ['document']
    insert_after = 'autocomplete_fields'
    extra = 0

class DocumentAdmin(ImageCroppingMixin, nested_admin.NestedModelAdmin):
    search_fields = ['word']
    inlines = [AlternativeWordAdmin]
    ordering = ['word']
    list_filter = ['training_sets__title']
    #list_filter = (TrainingSetListFilter, )
    

admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)