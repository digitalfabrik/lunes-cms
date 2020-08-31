"""
Map paths to view functions
"""
from django.urls import path  # pylint: disable=E0401

from . import views

urlpatterns = [  # pylint: disable=C0103
    path('', views.index, name='index'),
    path('sets', views.api_training_sets, name='sets'),
    path('set/<int:training_set_id>/documents',
         views.api_documents, name='documents'),
    path('alternative_words/<int:document_id>', views.api_alternative_words, name = 'alternative_words')
]
