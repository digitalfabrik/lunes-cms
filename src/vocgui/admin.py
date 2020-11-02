"""
Register models for Django's CRUD back end
"""
from django.contrib import admin  # pylint: disable=E0401
from .models import Discipline, TrainingSet, Document, AlternativeWord  # pylint: disable=E0401
from image_cropping import ImageCroppingMixin

"""
Specify autocomplete_fields and search_fields
"""
class DisciplineAdmin(admin.ModelAdmin):
    search_fields = ['title']

class TrainingSetAdmin(admin.ModelAdmin):
    search_fields = ['title']
    autocomplete_fields = ['discipline']

class DocumentAdmin(ImageCroppingMixin, admin.ModelAdmin):
    search_fields = ['word']
    autocomplete_fields = ['training_set']

class AlternativeWordAdmin(admin.ModelAdmin):
    search_fields = ['alt_word']
    autocomplete_fields = ['document']
    

admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(AlternativeWord, AlternativeWordAdmin)

