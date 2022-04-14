from django.contrib import admin

from ..models import AlternativeWord


class AlternativeWordAdmin(admin.StackedInline):
    """
    Admin Interface to for the AlternativeWord module.
    Inheriting from `admin.StackedInline`.
    """

    model = AlternativeWord
    search_fields = ["alt_word"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0
