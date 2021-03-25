"""
Register models for Django's CRUD back end
"""
from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord, DocumentImage  # pylint: disable=E0401
import nested_admin

"""
Specify autocomplete_fields, search_fields and nested modules
"""


class DisciplineAdmin(admin.ModelAdmin):
    search_fields = ['title']


class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['discipline']


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


admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
