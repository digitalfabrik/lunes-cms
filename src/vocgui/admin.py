"""
Register models for Django's CRUD back end
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin
from .list_filter import DisciplineListFilter, TrainingSetListFilter

"""
Specify autocomplete_fields and search_fields
"""


class DisciplineAdmin(admin.ModelAdmin):
    search_fields = ['title']
    ordering = ['title']


class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['discipline']
    ordering = ['discipline__title', 'title']
    list_filter = (DisciplineListFilter,)


class DocumentAdmin(ImageCroppingMixin, admin.ModelAdmin):
    search_fields = ['word']
    autocomplete_fields = ['training_set']
    ordering = ['training_set__discipline__title', 'training_set__title', 'word']
    list_filter = ('training_set__discipline', TrainingSetListFilter)


class AlternativeWordAdmin(admin.ModelAdmin):
    search_fields = ['alt_word']
    autocomplete_fields = ['document']


admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(AlternativeWord, AlternativeWordAdmin)
