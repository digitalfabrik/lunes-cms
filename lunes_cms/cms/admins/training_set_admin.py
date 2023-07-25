from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Count, F, Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ngettext

from mptt.admin import DraggableMPTTAdmin

from ..list_filter import DisciplineListFilter
from ..forms import TrainingSetForm
from ..models import Static, Document, Discipline
from ..utils import iter_to_string


class TrainingSetAdmin(DraggableMPTTAdmin):
    """
    Admin Interface to for the TrainigSet module.
    Inheriting from `mptt.admin.DraggableMPTTAdmin`.
    """

    exclude = ("creator_is_admin",)
    fields = [
        "released",
        "title",
        "description",
        "icon",
        "image_tag",
        "documents",
        "discipline",
        "created_by",
    ]
    readonly_fields = ["created_by", "image_tag"]
    search_fields = ["title"]
    form = TrainingSetForm
    list_display = [
        "tree_actions",
        "title",
        "released",
        "words",
        "words_released",
        "words_unreleased",
        "related_disciplines",
        "creator_group",
    ]
    list_display_links = ["title"]
    list_filter = [DisciplineListFilter, "released"]
    actions = ["make_released", "make_unreleased"]
    list_per_page = 25

    def get_list_display(self, request):
        if request.user.is_superuser:
            return [
                display for display in self.list_display if display not in ["words"]
            ]
        return [
            display
            for display in self.list_display
            if display not in ["words_released", "words_unreleased"]
        ]

    def save_model(self, request, obj, form, change):
        """
        Overwrite django built-in function to save
        user group and admin status of model

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
        :return: adjusted queryset
        :rtype: QuerySet
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.filter(creator_is_admin=True).annotate(
                words_released=Count(
                    "documents",
                    filter=Q(
                        documents__creator_is_admin=True,
                        documents__document_image__confirmed=True,
                    ),
                    distinct=True,
                ),
                words_unreleased=Count(
                    "documents",
                    filter=(
                        Q(documents__creator_is_admin=True)
                        & ~Q(documents__document_image__confirmed=True)
                    ),
                    distinct=True,
                ),
            )
        user_groups = request.user.groups.all()
        return qs.filter(created_by__in=user_groups).annotate(
            words=Count(
                "documents",
                filter=Q(documents__created_by__in=user_groups),
                distinct=True,
            ),
        )

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
        :return: model form with adjusted querysets
        :rtype: ModelForm
        """
        form = super(TrainingSetAdmin, self).get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields["discipline"].queryset = (
                Discipline.objects.filter(
                    created_by__in=request.user.groups.all(), lft=F("rght") - 1
                )
                .order_by("title")
                .order_by("level")
            )
            form.base_fields["documents"].queryset = (
                Document.objects.filter(
                    Q(created_by__in=request.user.groups.all())
                    | (
                        Q(creator_is_admin=True, document_image__confirmed=True)
                        & ~Q(audio="")
                    )
                )
                .distinct()
                .order_by("word")
            )
        else:
            form.base_fields["discipline"].queryset = (
                Discipline.objects.filter(creator_is_admin=True, lft=F("rght") - 1)
                .order_by("title")
                .order_by("level")
            )
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
        # Annotate queryset so it can be filtered by the document count later
        annotated_queryset = queryset.annotate(
            document_count=Count(
                "documents",
                filter=Q(documents__document_image__confirmed=True),
                distinct=True,
            )
        )
        # Split training sets by their validity and their "released" status
        invalid_trainingsets = []
        released_trainingsets = []
        unreleased_trainingsets = []
        for trainingset in annotated_queryset:
            if trainingset.document_count < settings.TRAININGSET_MIN_DOCS:
                invalid_trainingsets.append(trainingset)
            elif trainingset.released:
                released_trainingsets.append(trainingset)
            else:
                unreleased_trainingsets.append(trainingset)
        # Show error message for invalid trainingsets
        if invalid_trainingsets:
            messages.error(
                request,
                ngettext(
                    "The training set {} could not be released because it contains less than {} vocabulary words with confirmed images.",
                    "The training sets {} could not be released because they contain less than {} vocabulary words with confirmed images.",
                    len(invalid_trainingsets),
                ).format(
                    iter_to_string(invalid_trainingsets),
                    settings.TRAININGSET_MIN_DOCS,
                ),
            )
        # Show info message for valid trainingsets that are already released
        if released_trainingsets:
            messages.info(
                request,
                ngettext(
                    "The training set {} is already released.",
                    "The training sets {} are already released.",
                    len(released_trainingsets),
                ).format(iter_to_string(released_trainingsets)),
            )
        # Update valid trainingsets and show success message
        if unreleased_trainingsets:
            # Update valid queryset
            annotated_queryset.filter(
                document_count__gte=settings.TRAININGSET_MIN_DOCS
            ).update(released=True)
            messages.success(
                request,
                ngettext(
                    "The training set {} was successfully released.",
                    "The training sets {} were successfully released.",
                    len(unreleased_trainingsets),
                ).format(iter_to_string(unreleased_trainingsets)),
            )

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
        # Split all training sets by their "released" status
        released_trainingsets = []
        unreleased_trainingsets = []
        for trainingset in queryset:
            if trainingset.released:
                released_trainingsets.append(trainingset)
            else:
                unreleased_trainingsets.append(trainingset)
        # Add info messages for training sets that are already unreleased
        if unreleased_trainingsets:
            messages.info(
                request,
                ngettext(
                    "The training set {} is already unreleased.",
                    "The training sets {} are already unreleased.",
                    len(unreleased_trainingsets),
                ).format(iter_to_string(unreleased_trainingsets)),
            )
        # Get all training sets that are released and need to be updated
        if released_trainingsets:
            queryset.update(released=False)
            messages.success(
                request,
                ngettext(
                    "The training set {} was successfully unreleased.",
                    "The training sets {} were successfully unreleased.",
                    len(released_trainingsets),
                ).format(iter_to_string(released_trainingsets)),
            )

    @admin.display(
        description=_("words"),
        ordering="-words",
    )
    def words(self, obj):
        document_list = reverse("admin:cms_document_changelist")
        return mark_safe(
            f"<a href={document_list}?training+set={obj.id}>{obj.words}</a>"
        )

    @admin.display(
        description=_("published words"),
        ordering="-words_released",
    )
    def words_released(self, obj):
        document_list = reverse("admin:cms_document_changelist")
        return mark_safe(
            f"<a href={document_list}?training+set={obj.id}&images=approved>{obj.words_released}</a>"
        )

    @admin.display(
        description=_("unpublished words"),
        ordering="-words_unreleased",
    )
    def words_unreleased(self, obj):
        document_list = reverse("admin:cms_document_changelist")
        return mark_safe(
            f"<a href={document_list}?training+set={obj.id}&images=no-approved>{obj.words_unreleased}</a>"
        )

    def related_disciplines(self, obj):
        """
        Display related disciplines in list display

        :param obj: Training set object
        :type obj: models.TrainingSet
        :return: comma separated list of related disciplines
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

    class Media:
        js = ("js/image_preview.js",)
