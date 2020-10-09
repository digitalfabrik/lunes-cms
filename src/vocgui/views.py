"""
REST-Framework
"""
from django.http import HttpResponse  # pylint: disable=E0401
from django.core import serializers  # pylint: disable=E0401
from django.shortcuts import render  # pylint: disable=E0401
from rest_framework import viewsets

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

def index(request):  # pylint: disable=W0613
    """
    Display JS app that lets users train
    """
    # pylint: disable=E1101
    return render(request, 'index.html')


def api_training_sets(request):  # pylint: disable=W0613
    """
    API endpoint to get all training sets
    """
    training_sets = (TrainingSet.objects.all())
    training_set_list = serializers.serialize('json', training_sets)
    return HttpResponse(training_set_list, content_type="application/json")


def api_documents(request, training_set_id=None):  # pylint: disable=W0613
    """
    API endpoint to get all documents of a training set
    """
    documents = Document.objects.filter(training_set__id=training_set_id)
    documents_list = serializers.serialize('json', documents)
    return HttpResponse(documents_list, content_type="application/json")

def api_alternative_words(request, document_id=None):
    """
    API endpoint to get all alternative words of a document
    """

    alternative_words = AlternativeWord.objects.filter(document_id = document_id)
    alternative_words_list = serializers.serialize('json', alternative_words)
    return HttpResponse(alternative_words_list, content_type="application/json")

def api_report_template(request):
    """
    Load report template as html
    """
    return render(request, 'report.html')