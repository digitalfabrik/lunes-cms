from django import forms
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.utils.translation import ugettext_lazy as _
from mptt.models import TreeForeignKey

from .models import Document, TrainingSet, Discipline
from .widgets import ManyToManyOverlay


class DisciplineChoiceField(forms.ModelMultipleChoiceField):
    """
    Custom form field in order to include parent nodes in string representation.
    Inherits from `forms.ModelMultipleChocieField`.
    """

    def label_from_instance(self, obj):
        if obj.parent:
            ancestors = [
                node.title for node in obj.parent.get_ancestors(include_self=True)
            ]
            ancestors.append(obj.title)
            return " \u2794 ".join(ancestors)
        else:
            return obj.title


class TrainingSetForm(forms.ModelForm):
    """
    Defining custom form for the training set admin interface.
    Inherits from `forms.ModelForm`.
    """

    class Meta:
        """
        Defining Meta description of `TrainingSetForm`.
        """

        model = TrainingSet
        fields = ["released", "title", "description", "icon", "documents"]

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    discipline = DisciplineChoiceField(
        queryset=Discipline.objects.all(),
        widget=FilteredSelectMultiple(
            verbose_name=(_("disciplines")), is_stacked=False
        ),
        label=_("disciplines"),
    )
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.all(),
        widget=ManyToManyOverlay(verbose_name=(_("vocabulary")), is_stacked=False),
        label=_("vocabulary"),
        help_text=_(
            "Please select some vocabularies for your training set. To see a preview of the corresponding image and audio files, press the alt key while selecting."
        ),
    )

    def clean(self):
        """
        Make sure the training set is only released when it contains at least as many vocabularies as defined in
        :attr:`~lunes_cms.core.settings.TRAININGSET_MIN_DOCS`.

        :return: The cleaned data for this form
        :rtype: dict
        """
        cleaned_data = super().clean()
        documents = cleaned_data.get("documents")
        if cleaned_data.get("released") and (
            not documents
            or documents.filter(document_image__confirmed=True).count()
            < settings.TRAININGSET_MIN_DOCS
        ):
            self.add_error(
                "released",
                _(
                    "You can only release a training set that contains at least {} vocabulary words with confirmed images."
                ).format(settings.TRAININGSET_MIN_DOCS),
            )
        return cleaned_data
