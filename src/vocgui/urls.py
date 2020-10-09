"""
Map paths to view functions
"""
from django.urls import include, path # pylint: disable=E0401
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'fields', views.FieldsViewSet, 'fields')
router.register(r'training_set', views.TrainingSetViewSet, 'training_set') 
router.register(r'documents', views.DocumentViewSet, 'documents')
router.register(r'alt_words', views.AlternativeWordViewSet, 'alt_words') 

urlpatterns = [  # pylint: disable=C0103
    path('', views.index, name='index'),
    path('sets', views.api_training_sets, name='sets'),
    path('set/<int:training_set_id>/documents',
         views.api_documents, name='documents'),
    path('report', views.api_report_template, name='report_template'),
    path('alternative_words/<int:document_id>', views.api_alternative_words, name = 'alternative_words'),
    path('api/', include(router.urls))
]
