from __future__ import absolute_import, unicode_literals

import io
import re
from zipfile import ZipFile

from django.contrib import admin
from django.db.models import Count, Q
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mptt.admin import DraggableMPTTAdmin
from tablib import Dataset

from ..models import Discipline, Document, Static
from .document_resource import DocumentResource


class DisciplineAdmin(DraggableMPTTAdmin):
    """
    Admin Interface to for the Discipline module.
    Inheriting from `mptt.admin.DraggableMPTTAdmin`.
    """

    fields = [
        "released",
        "title",
        "description",
        "icon",
        "image_tag",
        "parent",
        "created_by",
    ]
    readonly_fields = ["created_by", "image_tag"]
    search_fields = ["title"]
    list_display = [
        "tree_actions",
        "indented_title",
        "released",
        "modules_released",
        "modules_unreleased",
        "words_released",
        "creator_group",
    ]
    list_display_links = ["indented_title"]
    list_filter = ["released"]
    actions = [
        "delete_selected",
        "make_released",
        "make_unreleased",
        "make_export_to_CSV",
    ]
    list_per_page = 25

    def get_list_display(self, request):
        if request.user.is_superuser:
            return self.list_display
        return [display for display in self.list_display if display != "words_released"]

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin status of model

        :param request: current user request
        :type request: django.http.request
        :param obj: discipline object
        :type obj: ~lunes_cms.cms.models.discipline.Discipline
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

    def get_action_choices(self, request, default_choices=""):
        """
        Overwrite django built-in function to modify action choices. The first
        option is dropped since it is a place holder.

        :param request: current user request
        :type request: django.http.request

        :return: modified action choices
        :rtype: dict
        """
        choices = super().get_action_choices(request)
        choices.pop(0)
        return choices

    def get_queryset(self, request):
        """
        Overwrite django built-in function to modify queryset according to user.
        Users that are not superusers only see disciplines of their groups.

        :param request: current user request
        :type request: django.http.request

        :return: adjusted queryset
        :rtype: QuerySet
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.filter(creator_is_admin=True).annotate(
                modules_released=Count(
                    "training_sets",
                    filter=Q(
                        training_sets__creator_is_admin=True,
                        training_sets__released=True,
                    ),
                    distinct=True,
                ),
                modules_unreleased=Count(
                    "training_sets",
                    filter=Q(
                        training_sets__creator_is_admin=True,
                        training_sets__released=False,
                    ),
                    distinct=True,
                ),
                children_modules_released=Count(
                    "children__training_sets",
                    filter=Q(
                        children__creator_is_admin=True,
                        children__training_sets__creator_is_admin=True,
                        children__training_sets__released=True,
                    ),
                    distinct=True,
                ),
                children_modules_unreleased=Count(
                    "children__training_sets",
                    filter=Q(
                        children__creator_is_admin=True,
                        children__training_sets__creator_is_admin=True,
                        children__training_sets__released=False,
                    ),
                    distinct=True,
                ),
                words_released=Count(
                    "training_sets__documents",
                    filter=Q(
                        training_sets__released=True,
                        training_sets__documents__creator_is_admin=True,
                        training_sets__documents__document_image__confirmed=True,
                    ),
                    distinct=True,
                ),
                children_words_released=Count(
                    "children__training_sets__documents",
                    filter=Q(
                        children__creator_is_admin=True,
                        children__training_sets__released=True,
                        children__training_sets__documents__creator_is_admin=True,
                        children__training_sets__documents__document_image__confirmed=True,
                    ),
                    distinct=True,
                ),
                modules_released_order=Greatest(
                    "modules_released", "children_modules_released"
                ),
                modules_unreleased_order=Greatest(
                    "modules_unreleased", "children_modules_unreleased"
                ),
                words_released_order=Greatest(
                    "words_released", "children_words_released"
                ),
            )
        user_groups = request.user.groups.all()
        return qs.filter(created_by__in=user_groups).annotate(
            modules_released=Count(
                "training_sets",
                filter=Q(
                    training_sets__created_by__in=user_groups,
                    training_sets__released=True,
                ),
                distinct=True,
            ),
            modules_unreleased=Count(
                "training_sets",
                filter=Q(
                    training_sets__created_by__in=user_groups,
                    training_sets__released=False,
                ),
                distinct=True,
            ),
            children_modules_released=Count(
                "children__training_sets",
                filter=Q(
                    children__created_by__in=user_groups,
                    children__training_sets__created_by__in=user_groups,
                    children__training_sets__released=True,
                ),
                distinct=True,
            ),
            children_modules_unreleased=Count(
                "children__training_sets",
                filter=Q(
                    children__created_by__in=user_groups,
                    children__training_sets__created_by__in=user_groups,
                    children__training_sets__released=False,
                ),
                distinct=True,
            ),
            modules_released_order=Greatest(
                "modules_released", "children_modules_released"
            ),
            modules_unreleased_order=Greatest(
                "modules_unreleased", "children_modules_unreleased"
            ),
        )

    def get_form(self, request, obj=None, change=False, **kwargs):
        """
        Overwrite django built-in function to define custom choices
        in MPTT many to many selector for parent disciplines,
        e.g. users should not see disciplines by superusers.
        The function modifies the querysets of the
        corresponding base fields dynamically.

        :param request: current user request
        :type request: django.http.request
        :param obj: django model object, defaults to None
        :type obj: django.db.models, optional

        :return: model form with adjusted querysets
        :rtype: ModelForm
        """
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["parent"].queryset = (
                Discipline.objects.filter(
                    created_by__in=request.user.groups.all(),
                    training_sets__isnull=True,
                )
                .order_by("title")
                .order_by("level")
            )
        else:
            form.base_fields["parent"].queryset = (
                Discipline.objects.filter(
                    creator_is_admin=True,
                    training_sets__isnull=True,
                )
                .order_by("title")
                .order_by("level")
            )
        return form

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

    @admin.action(description=_("Export all vocabulary for this discipline to CSV"))
    def make_export_to_CSV(self, request, queryset):
        """
        Export the documents of the selected disciplines.

        :param request: current user request
        :type request: django.http.request
        :param queryset: current queryset
        :type queryset: QuerySet
        """
        csvs = {}

        for profession in queryset:
            if profession.children.exists():
                continue
            resource = DocumentResource()

            dataset = Dataset(
                *(
                    resource.export_resource(obj)
                    for obj in Document.objects.filter(
                        training_sets__discipline=profession
                    )
                ),
                headers=resource.export().headers,
            )

            csvs[profession] = dataset.csv

        zip_buffer = io.BytesIO()

        with ZipFile(zip_buffer, "w") as zipfile:
            for profession, csv in csvs.items():
                zipfile.writestr(f"{make_safe_filename(profession.title)}.csv", csv)

        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="Lunes_vocabulary.zip"'
        return response

    @admin.display(
        description=_("released modules"),
        ordering="modules_released_order",
    )
    def modules_released(self, obj):
        """
        returns HTML Tag of the link to released training sets related to the discipline

        :param obj: Discipline object
        :type obj: ~lunes_cms.cms.models.discipline.Discipline

        :return: HTML Tag of the link to released training sets related to the discipline
        :rtype: str
        """
        if not obj.is_leaf_node():
            return obj.children_modules_released
        trainingset_list = reverse("admin:cms_trainingset_changelist")
        return mark_safe(
            f"<a href={trainingset_list}?disciplines={obj.id}&released__exact=1>{obj.modules_released}</a>"
        )

    @admin.display(
        description=_("unreleased modules"),
        ordering="modules_unreleased_order",
    )
    def modules_unreleased(self, obj):
        """
        returns HTML Tag of the link to unreleased training sets related to the discipline

        :param obj: Discipline object
        :type obj: ~lunes_cms.cms.models.discipline.Discipline

        :return: HTML Tag of the link to unreleased training sets related to the discipline
        :rtype: str
        """
        if not obj.is_leaf_node():
            return obj.children_modules_unreleased
        trainingset_list = reverse("admin:cms_trainingset_changelist")
        return mark_safe(
            f"<a href={trainingset_list}?disciplines={obj.id}&released__exact=0>{obj.modules_unreleased}</a>"
        )

    @admin.display(
        description=_("published words in released modules"),
        ordering="-words_released_order",
    )
    def words_released(self, obj):
        """
        returns HTML Tag of the link to released words in the relased training sets related to the descipline

        :param obj: Discipline object
        :type obj: ~lunes_cms.cms.models.discipline.Discipline

        :return:
        :rtype: str
        """
        if not obj.is_leaf_node():
            return obj.children_words_released
        document_list = reverse("admin:cms_document_changelist")
        return mark_safe(
            f"<a href={document_list}?disciplines={obj.id}&assigned=released&images=approved>{obj.words_released}</a>"
        )

    @admin.display(
        description=_("creator group"),
    )
    def creator_group(self, obj):
        """
        Include creator group of discipline in list display

        :param obj: Discipline object
        :type obj: ~lunes_cms.cms.models.discipline.Discipline

        :return: Either static admin group or user group
        :rtype: str
        """
        if obj.creator_is_admin:
            return Static.admin_group
        if obj.created_by:
            return obj.created_by
        return None

    class Media:
        """
        Media class for admin interface for disciplines
        """

        js = ("js/image_preview.js",)


def make_safe_filename(unsafe):
    """
    Method to create a safe filename with regex.
    """
    return re.sub(r"[^a-zA-Z0-9.äöüÄÖÜ]+", "_", unsafe)
