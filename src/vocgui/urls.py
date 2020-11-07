"""
Map paths to view functions
"""
from django.urls import include, path # pylint: disable=E0401
from rest_framework import routers
from django.conf.urls import url
from rest_framework_swagger.views import get_swagger_view

from . import views

router = routers.DefaultRouter()
router.register(r'disciplines', views.DisciplineViewSet, 'disciplines')
router.register(r'training_set/(?P<discipline_id>[0-9]+)', views.TrainingSetViewSet, 'training_set') 
router.register(r'documents/(?P<training_set_id>[0-9]+)', views.DocumentViewSet, 'documents')

schema_view = get_swagger_view(title='API Docs')

urlpatterns = [
    path('', views.redirect_view, name='redirect'),
    path('api/', include(router.urls)),
    path('docs/', schema_view),
]
