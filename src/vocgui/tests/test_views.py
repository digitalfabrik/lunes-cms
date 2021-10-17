"""
Tests for vocgui.views files
"""

from django.http import response
from django.test import TestCase
from rest_framework.test import APIClient
from vocgui.models import GroupAPIKey
from vocgui.models.discipline import Discipline
from vocgui.models.document import Document
from vocgui.models.training_set import TrainingSet
from django.urls import reverse
from rest_framework import status
from .utils import setup_db
from django.contrib.auth.models import Permission, User
from unittest.mock import patch
from django.core.exceptions import PermissionDenied

client = APIClient()

class TestViews(TestCase):
    def setUp(self):
        setup = setup_db()
        setup.basic_db_setup()
        global api_key
        api_key = setup.credentials["test-group"]
    
    def test_discipline_filtered_viewset(self):
        response = client.get('/api/disciplines_by_level/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        id = response.json()[0]["id"]
        response = client.get(f'/api/disciplines_by_level/{id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_training_set_viewset(self):
        discipline = Discipline.objects.get(title="Werkzeug")
        response = client.get(f'/api/training_set/{discipline.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_viewset(self):
        training_set = TrainingSet.objects.get(title="Grundlagen")
        response = client.get(f'/api/documents/{training_set.id}/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discipline_viewset(self):
        response = client.get('/api/disciplines/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_by_id(self):
        document = Document.objects.get(word="Hammer")
        user = User.objects.get(username="lunes")
        client.force_authenticate(user=user)
        response = client.get(f"/api/document_by_id/{document.id}/", format="json")
        client.force_authenticate(user=None)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group_view(self):
        client.credentials(HTTP_AUTHORIZATION='Api-Key ' + api_key)
        response = client.get(f"/api/group_info/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION="Api-Key INVALIDKEY")
        response = client.get(f"/api/group_info/", format="json")
        #self.assertEqual(response.status_code)
        #print(response.json())
        client.credentials(HTTP_AUTHORIZATION="INVALID KEY")