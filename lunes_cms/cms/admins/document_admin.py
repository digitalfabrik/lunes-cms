from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.db.models import Case, Exists, IntegerField, OuterRef, Value, When
from django.utils.translation import ugettext_lazy as _

from ..list_filter import (
    DocumentDisciplineListFilter,
    DocumentTrainingSetListFilter,
    ApprovedImageListFilter,
    AssignedListFilter,
)
from ..models import Static, DocumentImage
from .document_image_admin import DocumentImageAdmin
from .alternative_word_admin import AlternativeWordAdmin


SUPERUSER_ONLY_LIST_FILTERS = [ApprovedImageListFilter]


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
        AssignedListFilter,
        ApprovedImageListFilter,
    )
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin status of model

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
                obj.created_by = request.user.groups.all()[0]
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

        :return: adjusted queryset
        :rtype: QuerySet
        """
        qs = (
            super(DocumentAdmin, self)
            .get_queryset(request)
            .annotate(
                has_image=Exists(DocumentImage.objects.filter(document=OuterRef("pk"))),
                has_confirmed_image=Exists(
                    DocumentImage.objects.filter(
                        document=OuterRef("pk"), confirmed=True
                    )
                ),
                image_sort=Case(
                    When(has_confirmed_image=True, then=Value(2)),
                    When(has_image=True, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
        )
        if request.user.is_superuser:
            return qs.filter(creator_is_admin=True)
        return qs.filter(created_by__in=request.user.groups.all())

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

        :return: Whether the document has at least one confirmed image
        :rtype: bool
        """
        if obj.has_confirmed_image:
            return True
        if obj.has_image:
            return None
        return False

    has_image.boolean = True
    has_image.short_description = _("image")
    has_image.admin_order_field = "image_sort"

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

    def get_list_filter(self, request):
        """
        Override djangos get_list_filter function
        to remove specific list filters that are only relevant
        for super users.

        :param request: current request
        :type request: django.http.request
        :param obj: [description], defaults to None
        :type obj: django.db.models, optional

        :return: custom fields list
        :rtype: list[str]
        """
        if request.user.is_superuser:
            return self.list_filter
        # remove filters that are only relevant for super users
        filters = [f for f in self.list_filter if f not in SUPERUSER_ONLY_LIST_FILTERS]
        return tuple(filters)

    class Media:
        js = ("js/image_preview.js",)
