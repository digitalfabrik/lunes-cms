"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.forms.fields import NullBooleanField
from django.http.request import RAISE_ERROR

from image_cropping import ImageCroppingMixin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.utils.module_loading import import_module
from ordered_model.admin import OrderedModelAdmin
from functools import partial

from .models import (
    Discipline,
    TrainingSet,
    Document,
    AlternativeWord,
    DocumentImage,
    Static,
)
from .list_filter import (
    DisciplineListFilter,
    DocumentTrainingSetListFilter,
    DocumentDisciplineListFilter,
    ApprovedImageListFilter,
)
from .forms import TrainingSetForm


class DisciplineAdmin(OrderedModelAdmin):
    """
    Admin Interface to for the Discipline module.
    Inheriting from `admin.ModelAdmin`.
    """

    exclude = (
        "creator_is_admin",
    )
    readonly_fields = (
        "created_by",
    )
    search_fields = ["title"]
    actions = ["delete_selected", "make_released", "make_unreleased"]
    list_display = ("title", "released", "creator_group", "move_up_down_links")
    list_per_page = 25

    # Save user group and admin satus of model
    def save_model(self, request, obj, form, change):
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0]
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()

    # django actions to release/unrelease model
    @admin.action(description=_("Release selected disciplines"))
    def make_released(self, request, queryset):
        queryset.update(released=True)

    @admin.action(description=_("Unrelease selected disciplines"))
    def make_unreleased(self, request, queryset):
        queryset.update(released=False)

    def get_action_choices(self, request):
        choices = super(DisciplineAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    # function to display creator group in list display
    def creator_group(self, obj):
        if obj.creator_is_admin:
            return Static.admin_group
        elif obj.created_by:
            return obj.created_by
        else:
            return None

    creator_group.short_description = _("creator group")

    # only display models of the corresponding user group
    def get_queryset(self, request):
        qs = super(DisciplineAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by__in=request.user.groups.all())


class TrainingSetAdmin(OrderedModelAdmin):
    """
    Admin Interface to for the TrainigSet module.
    Inheriting from `admin.ModelAdmin`.
    """

    exclude = (
        "creator_is_admin",
    )
    readonly_fields = (
        "created_by",
    )
    search_fields = ["title"]
    form = TrainingSetForm
    list_display = (
        "title",
        "released",
        "related_disciplines",
        "creator_group",
        "move_up_down_links",
    )
    list_filter = (DisciplineListFilter,)
    actions = ["make_released", "make_unreleased"]
    list_per_page = 25

    # Save user group and admin satus of model
    def save_model(self, request, obj, form, change):
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0]
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()

    # django actions to release/unrelease model
    @admin.action(description=_("Release selected training sets"))
    def make_released(self, request, queryset):
        queryset.update(released=True)

    @admin.action(description=_("Unrelease selected training sets"))
    def make_unreleased(self, request, queryset):
        queryset.update(released=False)

    def get_action_choices(self, request):
        choices = super(TrainingSetAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    # fucntion to display related disciplines
    def related_disciplines(self, obj):
        return ", ".join([child.title for child in obj.discipline.all()])

    related_disciplines.short_description = _("disciplines")

    # function to display creator group in list display
    def creator_group(self, obj):
        if obj.creator_is_admin:
            return Static.admin_group
        elif obj.created_by:
            return obj.created_by
        else:
            return None

    creator_group.short_description = _("creator group")

    # only display models of the corresponding user group
    def get_queryset(self, request):
        qs = super(TrainingSetAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by__in=request.user.groups.all())

    # define custom choices in many to many selector
    def get_form(self, request, obj=None, **kwargs):
        form = super(TrainingSetAdmin, self).get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["discipline"].queryset = Discipline.objects.filter(
                created_by__in=request.user.groups.all()
            )
            form.base_fields["documents"].queryset = Document.objects.filter(
                created_by__in=request.user.groups.all()
            )
        else:
            form.base_fields["discipline"].queryset = Discipline.objects.filter(
                creator_is_admin=True
            )
            form.base_fields["documents"].queryset = Document.objects.filter(
                creator_is_admin=True
            )
        return form


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


class DocumentImageAdmin(admin.StackedInline):
    """
    Admin Interface to for the DocumentImage module.
    Inheriting from `admin.StackedInline`.
    """

    model = DocumentImage
    search_fields = ["name"]
    fields = ['name', 'image', 'image_tag', 'confirmed']
    readonly_fields = ['image_tag']
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []
        if not request.user.is_superuser:
            self.exclude.append('confirmed')
        return super(DocumentImageAdmin, self.get_form(request, obj, **kwargs))

class DocumentAdmin(admin.ModelAdmin):
    """
    Admin Interface to for the Document module.
    Inheriting from `admin.ModelAdmin`.
    """
    exclude = (
        "article_plural", # hide article_plural in admin
        "creator_is_admin"
    )
    readonly_fields = (
        "created_by",
    )
    search_fields = ["word"]
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
        DocumentTrainingSetListFilter,
        DocumentDisciplineListFilter,
        # ApprovedImageListFilter,
        
    )
    list_per_page = 25

    # Save user group and admin satus of model
    def save_model(self, request, obj, form, change):
        if not change:
            if len(request.user.groups.all()) >= 1:
                obj.created_by = request.user.groups.all()[0].name
            elif not request.user.is_superuser:
                raise IndexError("No group assigned. Please add the user to a group")
            obj.creator_is_admin = request.user.is_superuser
        obj.save()

    # function to display available action choices
    def get_action_choices(self, request):
        choices = super(DocumentAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    # fucntion to display related training sets
    def related_training_set(self, obj):
        return ", ".join([child.title for child in obj.training_sets.all()])

    related_training_set.short_description = _("training set")

    # function to display creator group in list display
    def creator_group(self, obj):
        if obj.creator_is_admin:
            return Static.admin_group
        elif obj.created_by:
            return obj.created_by
        else:
            return None
    creator_group.short_description = _("creator group")
    creator_group.admin_order_field = 'created_by'

    # function to display if the document has an audio 
    def has_audio(self, obj):
        if obj.audio:
            return True
        else:
            return False
    has_audio.boolean = True
    has_audio.short_description = _("audio")
    has_audio.admin_order_field = 'audio' 

    # function to display if the document has atleast one image
    def has_image(self, obj):
        if DocumentImage.objects.all().filter(document = obj):
            if DocumentImage.objects.all().filter(document = obj)[0].confirmed == True:
                return True
            elif DocumentImage.objects.all().filter(document = obj)[0].confirmed == False:
                return None
        return False
    has_image.boolean = True
    has_image.short_description = _("image")
    has_image.admin_order_field = 'document_image'
    
    # display article names instead of ids in list display
    def article_display(self, obj):
       return obj.get_article_display()
    article_display.short_description = _("article")

    # only display models of the corresponding user group
    def get_queryset(self, request):
        qs = super(DocumentAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(
            created_by__in=request.user.groups.values_list("name", flat=True).distinct()
        ) 


def get_app_list(self, request):
    """
    Function that returns a sorted list of all the installed apps that have been
    registered in this site.

    :param self: A handle to the :class:`admin.AdminSite`
    :type self: class: `admin.AdminSite`
    :param request: Current HTTP request
    :type request: HTTP request

    :return: list of app dictionaries (e.g. containing models)
    :rtype: list
    """
    ordering = {
        _("disciplines").capitalize(): 1,
        _("training sets").capitalize(): 2,
        _("vocabulary").capitalize(): 3,
    }
    app_dict = self._build_app_dict(request)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())

    # Sort the respective modules according the defined order
    for app in app_list:
        try:
            app["models"].sort(key=lambda x: ordering[x["name"]])
        except KeyError:
            pass
    return app_list


admin.AdminSite.get_app_list = get_app_list
admin.site.register(Discipline, DisciplineAdmin)
admin.site.register(TrainingSet, TrainingSetAdmin)
admin.site.register(Document, DocumentAdmin)
