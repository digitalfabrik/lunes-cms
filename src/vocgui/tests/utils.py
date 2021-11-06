from vocgui.models import Document, Discipline, TrainingSet, GroupAPIKey
from django.contrib.auth.models import User, Group


class setup_db:
    def __init__(self):
        self.credentials = {}

    def basic_db_setup(self):
        """[summary]

        Structure:
            Lunes
                - disciplines: Handwerker:in, Werkzeug (parent: Handwerker:in), Sicherheit (parent: Handwerker:in)
                - trainingsets: Werkzeug (linked to Handwerker:in and Hammer)
                - documents: Hammer, Säge
        """
        # Users and groups
        lunes = User.objects.create_user(
            username="lunes",
            email="lunes@user.com",
            password="lunes",
            is_staff=True,
            is_superuser=True,
        )
        test_group = Group.objects.create(name="test-group")
        api_key, key = GroupAPIKey.objects.create_key(
            name="test-group-key", organization=test_group
        )
        test_user = User.objects.create_user(
            username="test",
            email="test@user.com",
            password="test",
            is_staff=True,
            is_superuser=False,
        )
        test_user.groups.add(test_group)
        self.credentials[test_group.name] = key

        # Lunes documents
        doc_hammer = Document.objects.create(
            word_type="Nomen",
            word="Hammer",
            article=1,
            audio=None,
            creator_is_admin=True,
        )
        doc_saege = Document.objects.create(
            word_type="Nomen", word="Säge", article=2, audio=None, creator_is_admin=True
        )

        # Lunes disciplines
        discipline_handwerk = Discipline.objects.create(
            released=True, title="Handwerker:in", creator_is_admin=True
        )

        discipline_werkzeug = Discipline.objects.create(
            released=True,
            title="Werkzeug",
            parent=discipline_handwerk,
            creator_is_admin=True,
        )

        Discipline.objects.create(
            released=True,
            title="Sicherheit",
            parent=discipline_handwerk,
            creator_is_admin=True,
        )

        training_set = TrainingSet.objects.create(
            released=True, title="Grundlagen", creator_is_admin=True
        )
        training_set.documents.add(doc_hammer)
        training_set.discipline.add(discipline_werkzeug)

        # Group documents
        group_doc_hammer = Document.objects.create(
            word_type="Nomen",
            word="Test Hammer",
            article=1,
            audio=None,
            created_by=test_group.id,
            creator_is_admin=False,
        )
        group_doc_saege = Document.objects.create(
            word_type="Nomen",
            word="Test Säge",
            article=2,
            audio=None,
            created_by=test_group.id,
            creator_is_admin=False,
        )

        # Group disciplines
        group_discipline_handwerk = Discipline.objects.create(
            released=True,
            title="Test Handwerker:in",
            created_by=test_group,
            creator_is_admin=False,
        )

        group_discipline_werkzeug = Discipline.objects.create(
            released=True,
            title="Test Werkzeug",
            parent=group_discipline_handwerk,
            created_by=test_group,
            creator_is_admin=False,
        )

        Discipline.objects.create(
            released=True,
            title="Test Sicherheit",
            parent=group_discipline_handwerk,
            created_by=test_group,
            creator_is_admin=False,
        )

        group_training_set = TrainingSet.objects.create(
            released=True,
            title="Test Grundlagen",
            created_by=test_group,
            creator_is_admin=False,
        )
        group_training_set.documents.add(group_doc_hammer)
        group_training_set.discipline.add(group_discipline_werkzeug)
