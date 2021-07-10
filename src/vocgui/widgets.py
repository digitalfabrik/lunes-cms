from django.contrib.admin.widgets import FilteredSelectMultiple
import json

from .models import Document


class ManyToManyOverlay(FilteredSelectMultiple):
    class Media:
        js = (
            "js/jquery.min.js",
            "js/manytomany_overlay.js",
            "js/overlay.js",
        )
        css = {"all": ("css/overlay.css",)}

    def __init__(self, *args, **kwargs):
        return super(ManyToManyOverlay, self).__init__(
            attrs={"onclick": "document_overlay(event);"}, *args, **kwargs
        )
