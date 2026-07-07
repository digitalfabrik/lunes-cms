from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth import get_user_model
from django.db.models import Model
from django.template.loader import render_to_string
from django.test.client import Client
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper

from lunes_cms.cms.models import Discipline, Document, TrainingSet

if TYPE_CHECKING:
    # Client.post() returns this test-only response subclass (adds .content,
    # .context, .json(), etc.) — it doesn't inherit from HttpResponse, only
    # from the shared HttpResponseBase, so HttpResponse would be the wrong type.
    from django.test.client import _MonkeyPatchedWSGIResponse


@pytest.fixture(name="admin_client")
def admin_client_fixture(settings: SettingsWrapper) -> Client:
    """
    Create an authenticated admin client.

    :param settings: The pytest-django settings fixture
    :type settings: django.conf.LazySettings
    :return: Client logged in as superuser
    :rtype: django.test.client.Client
    """
    settings.ALLOWED_HOSTS = ["testserver"]
    user = get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password",
    )
    client = Client()
    client.force_login(user)
    return client


def post_delete_selected_confirmation(
    admin_client: Client,
    model_name: str,
    objects: list[Model],
    post: bool = False,
) -> _MonkeyPatchedWSGIResponse:
    """
    Post the admin delete-selected action for objects of a CMS model.

    :param admin_client: Logged-in Django test client
    :type admin_client: django.test.client.Client
    :param model_name: Admin URL model name
    :type model_name: str
    :param objects: Selected model objects
    :type objects: list[django.db.models.Model]
    :param post: Whether to confirm deletion
    :type post: bool
    :return: Admin response
    :rtype: django.http.HttpResponse
    """
    data = {
        "action": "delete_selected",
        ACTION_CHECKBOX_NAME: [obj.pk for obj in objects],
    }
    if post:
        data["post"] = "yes"
    return admin_client.post(reverse(f"admin:cms_{model_name}_changelist"), data)


@pytest.mark.django_db()
def test_delete_selected_single_discipline_shows_selected_name(
    admin_client: Client,
) -> None:
    """
    Verify that the bulk delete confirmation shows a single selected discipline name.

    :param admin_client: Logged-in Django test client
    :type admin_client: django.test.client.Client
    """
    discipline = Discipline.objects.create(title="Electrical Engineering")

    response = post_delete_selected_confirmation(
        admin_client, "discipline", [discipline]
    )

    content = response.content.decode()
    assert response.status_code == 200
    assert "Electrical Engineering" in content
    assert '""? It eventually will delete' not in content


@pytest.mark.django_db()
def test_delete_selected_three_documents_shows_all_selected_names(
    admin_client: Client,
) -> None:
    """
    Verify that three selected documents are all listed on the confirmation page.

    :param admin_client: Logged-in Django test client
    :type admin_client: django.test.client.Client
    """
    documents = [
        Document.objects.create(word=f"Tool {index}", singular_article=1)
        for index in range(1, 4)
    ]

    response = post_delete_selected_confirmation(admin_client, "document", documents)

    content = response.content.decode()
    assert response.status_code == 200
    for document in documents:
        assert document.word in content
    assert "more objects will be deleted" not in content


@pytest.mark.django_db()
def test_delete_selected_five_training_sets_shows_first_three_and_remainder(
    admin_client: Client,
) -> None:
    """
    Verify that five selected training sets are truncated after three names.

    :param admin_client: Logged-in Django test client
    :type admin_client: django.test.client.Client
    """
    training_sets = [
        TrainingSet.objects.create(title=f"Training set {index}")
        for index in range(1, 6)
    ]

    response = post_delete_selected_confirmation(
        admin_client, "trainingset", training_sets
    )

    content = response.content.decode()
    assert response.status_code == 200
    for training_set in training_sets[:3]:
        assert training_set.title in content
    assert training_sets[3].title not in content
    assert training_sets[4].title not in content
    assert "and 2 more objects will be deleted" in content
    for training_set in training_sets:
        assert f'name="{ACTION_CHECKBOX_NAME}" value="{training_set.pk}"' in content


@pytest.mark.django_db()
def test_delete_selected_post_deletes_full_selected_queryset(
    admin_client: Client,
) -> None:
    """
    Verify that confirming the action deletes every selected object.

    :param admin_client: Logged-in Django test client
    :type admin_client: django.test.client.Client
    """
    training_sets = [
        TrainingSet.objects.create(title=f"Training set {index}")
        for index in range(1, 6)
    ]

    response = post_delete_selected_confirmation(
        admin_client, "trainingset", training_sets, post=True
    )

    assert response.status_code == 302
    assert not TrainingSet.objects.filter(
        pk__in=[training_set.pk for training_set in training_sets]
    ).exists()


def test_object_delete_summary_hides_training_set_relationships() -> None:
    """
    Verify that the delete summary table omits training set relationship rows.
    """
    content = render_to_string(
        "admin/object_delete_summary.html",
        {
            "model_count": [
                ("training sets", 5),
                ("trainingset-document relationships", 3),
                ("trainingset-discipline relationships", 2),
                ("training set-document relationships", 3),
                ("training set-discipline relationships", 2),
            ]
        },
    )

    assert "Training sets" in content
    assert "trainingset-document relationships" not in content
    assert "trainingset-discipline relationships" not in content
    assert "training set-document relationships" not in content
    assert "training set-discipline relationships" not in content
