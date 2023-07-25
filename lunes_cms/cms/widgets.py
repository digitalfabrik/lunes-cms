from django.contrib.admin.widgets import FilteredSelectMultiple
from django.urls import reverse_lazy


class ManyToManyOverlay(FilteredSelectMultiple):
    """Adds an overlay to the `FilteredSelectMultiple`
    widget to preview images and audios of Document objects.
    Inherits from `django.contrib.admin.widgets.FilteredSelectMultiple`.
    """

    class Media:
        js = (
            "js/manytomany_overlay.js",
            "js/overlay.js",
            reverse_lazy("javascript-translations"),
        )
        css = {"all": ("css/overlay.css",)}

    def __init__(self, *args, **kwargs):
        """
        Instantiates model by calling `super()` and passing a new `onclick`
        event to the widget.
        """
        return super(ManyToManyOverlay, self).__init__(
            attrs={"onclick": "document_overlay(event);"}, *args, **kwargs
        )
