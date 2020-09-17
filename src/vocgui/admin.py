"""
Register models for Django's CRUD back end
"""
from django.contrib import admin  # pylint: disable=E0401
from .models import TrainingSet, Document, AlternativeWord  # pylint: disable=E0401
#from image_cropping import ImageCroppingMixin

#class MyModelAdmin(ImageCroppingMixin, admin.ModelAdmin):
#    pass


admin.site.register(TrainingSet)
admin.site.register(Document)
admin.site.register(AlternativeWord)
#admin.site.register(MyModelAdmin)
