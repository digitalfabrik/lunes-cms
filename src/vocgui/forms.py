from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .models import Document, TrainingSet, Discipline


class TrainingSetForm(forms.ModelForm):
    class Meta:
        model = TrainingSet
        fields = ['title', 'description', 'icon', 'discipline', 'documents']

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    discipline = forms.ModelChoiceField(queryset=Discipline.objects.all(), label=_('Bereich'))
    documents = forms.ModelMultipleChoiceField(
        queryset=Document.objects.all(),
        widget=FilteredSelectMultiple(
            verbose_name=(_('Wörter')),
            is_stacked=False
        ),
        label=_('Vokabeln')
    )
