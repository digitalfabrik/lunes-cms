"""
REST-Framework
"""
from django.http import HttpResponse  # pylint: disable=E0401
from django.core import serializers  # pylint: disable=E0401
from django.shortcuts import render  # pylint: disable=E0401
from rest_framework import viewsets
from django.shortcuts import redirect

from .models import TrainingSet, Document, AlternativeWord, Field
from .serializers import FieldSerializer, DocumentSerializer, TrainingSetSerializer, AlternativeWordSerializer

class FieldsViewSet(viewsets.ModelViewSet):
    queryset = Field.objects.all()
    serializer_class = FieldSerializer

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