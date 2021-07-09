from django.contrib.admin.widgets import FilteredSelectMultiple
import json

from .models import Document

class ManyToManyOverlay(FilteredSelectMultiple):
    class Media:
        js = ("js/manytomany_overlay.js",)

    def __init__(self, *args, **kwargs):
        return super(ManyToManyOverlay, self).__init__(
            attrs = {'onchange' : "document_overlay(this.value);"},
            *args, **kwargs
            )