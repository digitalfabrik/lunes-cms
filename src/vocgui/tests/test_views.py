"""
Tests for vocgui.views files
"""

from django.test import TestCase
from rest_framework.test import APIClient
from vocgui.models import GroupAPIKey
from vocgui.models.discipline import Discipline
from vocgui.models.document import Document
from vocgui.models.training_set import TrainingSet
from rest_framework import status
from django.contrib.auth.models import Group, User

client = APIClient()


class TestViews(TestCase):
    def setUp(self):
        self.lunes = User.objects.create_user(
            username="lunes",
            email="lunes@user.com",
            password="lunes",
            is_staff=True,
            is_superuser=True,
        )
        self.test_group = Group.objects.create(name="test-group")
        self.api_key, self.key = GroupAPIKey.objects.create_key(
            name="test-group-key", organization=self.test_group
        )
        test_user = User.objects.create_user(
            username="test",
            email="test@user.com",
            password="test",
            is_staff=True,
            is_superuser=False,
        )
        test_user.groups.add(self.test_group)

        # Lunes documents
        self.doc_hammer = Document.objects.create(
            word_type="Nomen",
            word="Hammer",
            article=1,
            audio=None,
            creator_is_admin=True,
        )
        self.doc_saege = Document.objects.create(
            word_type="Nomen", word="Säge", article=2, audio=None, creator_is_admin=True
        )

        # Lunes disciplines
        self.discipline_handwerk = Discipline.objects.create(
            released=True, title="Handwerker:in", creator_is_admin=True
        )

        self.discipline_werkzeug = Discipline.objects.create(
            released=True,
            title="Werkzeug",
            parent=self.discipline_handwerk,
            creator_is_admin=True,
        )

        self.discipline_sicherheit = Discipline.objects.create(
            released=True,
            title="Sicherheit",
            parent=self.discipline_handwerk,
            creator_is_admin=True,
        )

        self.training_set = TrainingSet.objects.create(
            released=True, title="Grundlagen", creator_is_admin=True
        )
        self.training_set.documents.add(self.doc_hammer)
        self.training_set.discipline.add(self.discipline_werkzeug)

        # Group documents
        self.group_doc_hammer = Document.objects.create(
            word_type="Nomen",
            word="Test Hammer",
            article=1,
            audio=None,
            created_by=self.test_group.id,
            creator_is_admin=False,
        )
        self.group_doc_saege = Document.objects.create(
            word_type="Nomen",
            word="Test Säge",
            article=2,
            audio=None,
            created_by=self.test_group.id,
            creator_is_admin=False,
        )

        # Group disciplines
        self.group_discipline_handwerk = Discipline.objects.create(
            released=True,
            title="Test Handwerker:in",
            created_by=self.test_group,
            creator_is_admin=False,
        )

        self.group_discipline_werkzeug = Discipline.objects.create(
            released=True,
            title="Test Werkzeug",
            parent=self.group_discipline_handwerk,
            created_by=self.test_group,
            creator_is_admin=False,
        )

        self.group_discipline_sicherheit = Discipline.objects.create(
            released=True,
            title="Test Sicherheit",
            parent=self.group_discipline_handwerk,
            created_by=self.test_group,
            creator_is_admin=False,
        )

        group_training_set = TrainingSet.objects.create(
            released=True,
            title="Test Grundlagen",
            created_by=self.test_group,
            creator_is_admin=False,
        )
        group_training_set.documents.add(self.group_doc_hammer)
        group_training_set.discipline.add(self.group_discipline_werkzeug)

    def test_discipline_filtered_viewset(self):
        response = client.get("/api/disciplines_by_level/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        id = response.json()[0]["id"]
        response = client.get(f"/api/disciplines_by_level/{id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = client.get(
            f"/api/disciplines_by_group/{self.test_group.id}/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        client.credentials(HTTP_AUTHORIZATION="Api-Key " + self.key)
        response = client.get(
            f"/api/disciplines_by_group/{self.test_group.id}/", format="json"
        )
        client.credentials(HTTP_AUTHORIZATION="")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_training_set_viewset(self):
        response = client.get(
            f"/api/training_set/{self.discipline_werkzeug.id}/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_viewset(self):
        training_set = TrainingSet.objects.get(title="Grundlagen")
        response = client.get(f"/api/documents/{self.training_set.id}/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_discipline_viewset(self):
        response = client.get("/api/disciplines/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_document_by_id(self):
        client.force_authenticate(user=self.lunes)
        response = client.get(
            f"/api/document_by_id/{self.doc_hammer.id}/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.force_authenticate(user=None)
        response = client.get(
            f"/api/document_by_id/{self.doc_hammer.id}/", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_view(self):
        client.credentials(HTTP_AUTHORIZATION="Api-Key " + self.key)
        response = client.get(f"/api/group_info/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION="Api-Key INVALIDKEY")
        response = client.get(f"/api/group_info/", format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        client.credentials(HTTP_AUTHORIZATION="")
