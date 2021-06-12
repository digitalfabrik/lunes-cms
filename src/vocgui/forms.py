from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .models import Document, TrainingSet, Discipline


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
    discipline = forms.ModelMultipleChoiceField(
        queryset=Discipline.objects.all().filter().order_by("title"),
        widget=FilteredSelectMultiple(
            verbose_name=(_("disciplines")), is_stacked=False
        ),
        label=_("disciplines"),
    )
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.all().order_by("word"),
        widget=FilteredSelectMultiple(verbose_name=(_("vocabulary")), is_stacked=False),
        label=_("vocabulary"),
    )
