"""
REST-Framework
"""
from django.http import HttpResponse  # pylint: disable=E0401
from django.core import serializers  # pylint: disable=E0401
from django.shortcuts import render  # pylint: disable=E0401
from rest_framework import viewsets
from django.shortcuts import redirect

from .models import TrainingSet, Document, AlternativeWord, Discipline
from .serializers import DisciplineSerializer, DocumentSerializer, TrainingSetSerializer, AlternativeWordSerializer

class DisciplineViewSet(viewsets.ModelViewSet):
    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    def get_queryset(self):
        user = self.request.user
        queryset = Document.objects.filter(training_set_id=self.kwargs['training_set_id'])
        return queryset

class TrainingSetViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingSetSerializer
    def get_queryset(self):
        user = self.request.user
        queryset = TrainingSet.objects.filter(discipline_id=self.kwargs['discipline_id'])
        return queryset

def redirect_view(request):
    """
    Redirect root URL
    """
    return redirect('api/')
