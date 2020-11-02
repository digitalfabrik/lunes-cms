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
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

class AlternativeWordViewSet(viewsets.ModelViewSet):
    queryset = AlternativeWord.objects.all()
    serializer_class = AlternativeWordSerializer

class TrainingSetViewSet(viewsets.ModelViewSet):
    queryset = TrainingSet.objects.all()
    serializer_class = TrainingSetSerializer

def redirect_view(request):
    """
    Redirect root URL
    """
    return redirect('api/')
