"""
REST-Framework
"""
from django.http import HttpResponse  # pylint: disable=E0401
from django.core import serializers  # pylint: disable=E0401
from django.shortcuts import render  # pylint: disable=E0401
from rest_framework import viewsets
from django.shortcuts import redirect
from django.db.models import Count

from .models import TrainingSet, Document, AlternativeWord, Discipline
from .serializers import DisciplineSerializer, DocumentSerializer, TrainingSetSerializer, AlternativeWordSerializer

class DisciplineViewSet(viewsets.ModelViewSet):
    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Discipline.objects.none()
        return Discipline.objects.annotate(
            total_training_sets=Count('training_sets')
        )

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()
        user = self.request.user
        queryset = Document.objects.filter(training_set_id=self.kwargs['training_set_id'])
        return queryset

class TrainingSetViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingSetSerializer
    serializer_class = TrainingSetSerializer
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrainingSet.objects.none()
        user = self.request.user
        queryset = TrainingSet.objects.filter(discipline_id=self.kwargs['discipline_id'])
        queryset = queryset.annotate(total_documents=Count('documents'))
        return queryset

def redirect_view(request):
    """
    Redirect root URL
    """
    return redirect('api/')
