"""
Tests for vocgui.utils files
"""

import string
from django.test import TestCase
from vocgui.models import Document
from vocgui.models.discipline import Discipline
from vocgui.models.training_set import TrainingSet
from vocgui.utils import (
    get_random_key,
    document_to_string,
    get_child_count,
    create_ressource_path,
    get_training_set_count,
)


class TestUtils(TestCase):
    def setUp(self):
        Document.objects.create(
            word_type="Nomen",
            word="Hammer",
            article=1,
            audio=None,
        )
        Document.objects.create(
            word_type="Nomen",
            word="Säge",
            article=2,
            audio=None,
        )
        Discipline.objects.create(released=True, title="Handwerker:in")
        Discipline.objects.create(
            released=True,
            title="Werkzeug",
            parent=Discipline.objects.get(title="Handwerker:in"),
        )

    def test_get_random_key(self):
        excluded_chars = list(string.ascii_uppercase)
        key = get_random_key(30, excluded_chars)
        self.assertEqual(30, len(key))
        for char in excluded_chars:
            self.assertNotIn(char, key)

    def test_document_to_string(self):
        tiger = Document.objects.get(word="Hammer")
        schlange = Document.objects.get(word="Säge")
        tiger_to_string = document_to_string(tiger)
        schlange_to_string = document_to_string(schlange)
        self.assertEqual(tiger_to_string, "(der) Hammer")
        self.assertEqual(schlange_to_string, "(die) Säge")

    def test_get_child_count(self):
        # no valid disciplines
        parent = Discipline.objects.get(title="Handwerker:in")
        child = Discipline.objects.get(title="Werkzeug")
        child_count = get_child_count(parent)
        self.assertEqual(0, child_count)

        # add training set to child
        training_set = TrainingSet.objects.create(
            released=True,
            title="Grundlagen",
        )
        training_set.documents.add(Document.objects.get(word="Hammer"))
        training_set.discipline.add(child)
        training_set.save()
        child_count = get_child_count(parent)
        self.assertEqual(1, child_count)

        # create another empty child
        second_child = Discipline.objects.create(
            released=True,
            title="Werkzeug Teil 2",
            parent=Discipline.objects.get(title="Handwerker:in"),
        )
        child_count = get_child_count(parent)
        self.assertEqual(1, child_count)

        # add training set to second child
        training_set.discipline.add(second_child)
        child_count = get_child_count(parent)
        self.assertEqual(2, child_count)

    def test_create_ressource_path(self):
        first_path = create_ressource_path("/home/user", "img.png")
        for i in range(5):
            second_path = create_ressource_path("/home/user", "img.png")
            self.assertNotEqual(first_path, second_path)

    def test_get_training_set_count(self):
        # no valid disciplines
        parent = Discipline.objects.get(title="Handwerker:in")
        child = Discipline.objects.get(title="Werkzeug")
        training_set_count = get_training_set_count(parent)
        self.assertEqual(0, training_set_count)

        # add training set to child
        training_set = TrainingSet.objects.create(
            released=True,
            title="Grundlagen",
        )
        training_set.documents.add(Document.objects.get(word="Hammer"))
        training_set.discipline.add(child)
        training_set.save()
        training_set_count = get_training_set_count(parent)
        self.assertEqual(1, training_set_count)

        # create another empty child
        second_child = Discipline.objects.create(
            released=True,
            title="Werkzeug Teil 2",
            parent=Discipline.objects.get(title="Handwerker:in"),
        )
        second_child.save()
        child_count = get_child_count(parent)
        self.assertEqual(1, child_count)

        # add training set to second child
        training_set.discipline.add(second_child)
        training_set_count = get_child_count(parent)
        self.assertEqual(2, training_set_count)

        # add unreleased training set
        second_training_set = TrainingSet.objects.create(
            released=False,
            title="Grundlagen Teil 2",
        )
        second_training_set.documents.add(Document.objects.get(word="Hammer"))
        second_training_set.discipline.add(child)
        training_set_count = get_child_count(parent)
        self.assertEqual(2, training_set_count)
