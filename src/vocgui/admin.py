"""
Register models for Django's CRUD back end
"""
from django.contrib import admin  # pylint: disable=E0401
from .models import Field, TrainingSet, Document, AlternativeWord  # pylint: disable=E0401

"""
Specify autocomplete_fields and search_fields
"""
class FieldAdmin(admin.ModelAdmin):
    search_fields = ['title']

class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['field']

class DocumentAdmin(admin.ModelAdmin):
    search_fields = ['word']
    autocomplete_fields = ['training_set']

class AlternativeWordAdmin(admin.ModelAdmin):
    autocomplete_fields = ['document']
    

admin.site.register(Field, FieldAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(AlternativeWord, AlternativeWordAdmin)

