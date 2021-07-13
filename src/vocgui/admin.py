"""
Register models for Django's CRUD back end and
specify autocomplete_fields, search_fields and nested modules
"""
from __future__ import absolute_import, unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from ordered_model.admin import OrderedModelAdmin

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
    Inheriting from `ordered_model.admin.OrderedModelAdmin`.
    """

    exclude = ("creator_is_admin",)
    readonly_fields = ("created_by",)
    search_fields = ["title"]
    actions = ["delete_selected", "make_released", "make_unreleased"]
    list_display = ("title", "released", "creator_group", "move_up_down_links")
    list_per_page = 25

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin satus of model

        :param request: current user request
        :type request: django.http.request
        :param obj: discipline object
        :type obj: models.Discipline
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
        choices = super(DisciplineAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    def get_queryset(self, request):
        """
        Overwrite django built-in function to modify queryset according to user.
        Users that are not superusers only see disciplines of their groups.

        :param request: current user request
        :type request: django.http.request
        :return: adjustet queryset
        :rtype: QuerySet
        """
        qs = super(DisciplineAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by__in=request.user.groups.all())

    @admin.action(description=_("Release selected disciplines"))
    def make_released(self, request, queryset):
        """
        Action to release discipline objects. It sets the
        corresponding boolean field to true.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        queryset.update(released=True)

    @admin.action(description=_("Unrelease selected disciplines"))
    def make_unreleased(self, request, queryset):
        """
        Action to hide discipline objects. It sets the
        corresponding boolean field to false.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        queryset.update(released=False)

    def creator_group(self, obj):
        """
        Include creator group of discipline in list display

        :param obj: Discipline object
        :type obj: models.Discipline
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


class TrainingSetAdmin(OrderedModelAdmin):
    """
    Admin Interface to for the TrainigSet module.
    Inheriting from `ordered_model.admin.OrderedModelAdmin`.
    """

    exclude = ("creator_is_admin",)
    readonly_fields = ("created_by",)
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

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin satus of model

        :param request: current user request
        :type request: django.http.request
        :param obj: training set object
        :type obj: models.TrainingSet
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
        choices = super(TrainingSetAdmin, self).get_action_choices(request)
        choices.pop(0)
        return choices

    def get_queryset(self, request):
        """
        Overwrite django built-in function to modify queryset according to user.
        Users that are not superusers only see training set of their groups.

        :param request: current user request
        :type request: django.http.request
        :return: adjustet queryset
        :rtype: QuerySet
        """
        qs = super(TrainingSetAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(created_by__in=request.user.groups.all())

    def get_form(self, request, obj=None, **kwargs):
        """
        Overwrite django built-in function to define custom choices
        in many to many selectors, e.g. users should not see documents
        by superusers. The function modifies the querysets of the
        corresponding base fields dynamically.

        :param request: current user request
        :type request: django.http.request
        :param obj: django model object, defaults to None
        :type obj: django.db.models, optional
        :return: model form with adjustet querysets
        :rtype: ModelForm
        """
        form = super(TrainingSetAdmin, self).get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["discipline"].queryset = Discipline.objects.filter(
                created_by__in=request.user.groups.all()
            ).order_by("title")
            form.base_fields["documents"].queryset = Document.objects.filter(
                created_by__in=request.user.groups.all()
            ).order_by("word")
        else:
            form.base_fields["discipline"].queryset = Discipline.objects.filter(
                creator_is_admin=True
            ).order_by("title")
            form.base_fields["documents"].queryset = Document.objects.filter(
                creator_is_admin=True
            ).order_by("word")
        return form

    @admin.action(description=_("Release selected training sets"))
    def make_released(self, request, queryset):
        """
        Action to release training set objects. It sets the
        corresponding boolean field to true.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        queryset.update(released=True)

    @admin.action(description=_("Unrelease selected training sets"))
    def make_unreleased(self, request, queryset):
        """
        Action to hide discipline objects. It sets the
        corresponding boolean field to false.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        queryset.update(released=False)

    def related_disciplines(self, obj):
        """
        Display related disciplines in list display

        :param obj: Training set object
        :type obj: models.TrainingSet
        :return: comma seperated list of related disciplines
        :rtype: str
        """
        return ", ".join([child.title for child in obj.discipline.all()])

    related_disciplines.short_description = _("disciplines")

    def creator_group(self, obj):
        """
        Include creator group of discipline in list display

        :param obj: Training set object
        :type obj: models.TrainingSet
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
    fields = ["name", "image", "image_tag", "confirmed"]
    readonly_fields = ["image_tag"]
    autocomplete_fields = ["document"]
    insert_after = "autocomplete_fields"
    extra = 0

    def get_form(self, request, obj=None, **kwargs):
        """
        Modify user form since normal users shouldn't
        see a confirmed button. This is only neccessary
        for superusers.

        :param request: current user request
        :type request: django.http.request
        :param obj: django model object, defaults to None
        :type obj: django.db.models, optional
        :return: model form with adjustet fields
        :rtype: ModelForm
        """
        self.exclude = []
        if not request.user.is_superuser:
            self.exclude.append("confirmed")
        return super(DocumentImageAdmin, self.get_form(request, obj, **kwargs))


class DocumentAdmin(admin.ModelAdmin):
    """
    Admin Interface to for the Document module.
    Inheriting from `admin.ModelAdmin`.
    """

    exclude = ("article_plural", "creator_is_admin")  # hide article_plural in admin
    readonly_fields = ("created_by",)
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

    # fucntion to display related training sets
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

    # display article names instead of ids in list display
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


def get_app_list(self, request):
    """
    Function that returns a sorted list of all the installed apps that have been
    registered in this site.

    :param self: A handle to the :class:`admin.AdminSite`
    :type self: class: `admin.AdminSite`
    :param request: current user request
    :type request: django.http.request

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
