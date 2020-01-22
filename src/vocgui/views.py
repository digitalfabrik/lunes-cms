"""
Simple REST API
"""
from django.http import HttpResponse  # pylint: disable=E0401
from django.core import serializers  # pylint: disable=E0401
from django.shortcuts import render  # pylint: disable=E0401

from .models import TrainingSet, Document


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
