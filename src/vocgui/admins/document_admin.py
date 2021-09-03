from __future__ import absolute_import, unicode_literals
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .document_image_admin import DocumentImageAdmin
from .alternative_word_admin import AlternativeWordAdmin
from vocgui.list_filter import (
    DocumentDisciplineListFilter,
    DocumentTrainingSetListFilter,
    ApprovedImageListFilter,
)
from vocgui.models import Static, DocumentImage


class DocumentAdmin(admin.ModelAdmin):
    """
    Admin Interface to for the Document module.
    Inheriting from `admin.ModelAdmin`.
    """

    exclude = ("article_plural", "creator_is_admin")
    readonly_fields = ("created_by",)
    search_fields = ["word", "alternatives__alt_word"]
    inlines = [DocumentImageAdmin, AlternativeWordAdmin]
    ordering = ["word", "creation_date"]
    list_display = (
        "word",
        "word_type",
        "article_display",
        "related_training_set",
        "has_audio",
        "has_image",
        "creator_group",
        "creation_date",
    )
    list_filter = (
        DocumentDisciplineListFilter,
        DocumentTrainingSetListFilter,
        ApprovedImageListFilter,
    )
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin satus of model

        :param request: current user request
        :type request: django.http.request
        :param obj: document object
        :type obj: models.Document
        :param form: employed model form
        :type form: ModelForm
        :param change: True if change on existing model
        :type change: bool
        :raises IndexError: Error when user is not superuser and doesn't belong to any group
        """
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0].name
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()

    def get_action_choices(self, request):
        """
        Overwrite django built-in function to modify action choices. The first
        option is dropped since it is a place holder.

        :param request: current user request
        :type request: django.http.request
        :return: modified action choices
        :rtype: dict
        """
        choices = super(DocumentAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    def get_queryset(self, request):
        """
        Overwrite django built-in function to modify queryset according to user.
        Users that are not superusers only see documents of their groups.

        :param request: current user request
        :type request: django.http.request
        :return: adjustet queryset
        :rtype: QuerySet
        """
        qs = super(DocumentAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            created_by__in=request.user.groups.values_list("name", flat=True).distinct()
        )

    def related_training_set(self, obj):
        """
        Display related training sets in list display

        :param obj: Document object
        :type obj: models.Document
        :return: comma seperated list of related training sets
        :rtype: str
        """
        return ", ".join([child.title for child in obj.training_sets.all()])

    related_training_set.short_description = _("training set")

    def creator_group(self, obj):
        """
        Include creator group of discipline in list display

        :param obj: Document object
        :type obj: models.Document
        :return: Either static admin group or user group
        :rtype: str
        """
        if obj.creator_is_admin:
            return Static.admin_group
        elif obj.created_by:
            return obj.created_by
        else:
            return None

    creator_group.short_description = _("creator group")
    creator_group.admin_order_field = "created_by"

    def has_audio(self, obj):
        """
        Include in list display whether a document has an audio file.

        :param obj: Document object
        :type obj: models.Document
        :return: Either static admin group or user group
        :rtype: str
        """
        if obj.audio:
            return True
        else:
            return False

    has_audio.boolean = True
    has_audio.short_description = _("audio")
    has_audio.admin_order_field = "audio"

    def has_image(self, obj):
        """
        Include in list display whether a document has an image file.

        :param obj: Document object
        :type obj: models.Document
        :return: Either static admin group or user group
        :rtype: str
        """
        if DocumentImage.objects.all().filter(document=obj):
            if DocumentImage.objects.all().filter(document=obj)[0].confirmed == True:
                return True
            elif DocumentImage.objects.all().filter(document=obj)[0].confirmed == False:
                return None
        return False

    has_image.boolean = True
    has_image.short_description = _("image")
    has_image.admin_order_field = "document_image"

    def article_display(self, obj):
        """
        Include article of document in list display

        :param obj: Document object
        :type obj: models.Document
        :return: Either static admin group or user group
        :rtype: str
        """
        return obj.get_article_display()

    article_display.short_description = _("article")
