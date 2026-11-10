"""
This module contains shared fixtures for pytest
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import Client
from pytest_django.plugin import DjangoDbBlocker

#: The migration that creates the default image prompt.
image_prompt_migration = importlib.import_module(
    "lunes_cms.cmsv2.migrations.0053_imageprompt"
)


# pylint: disable=unused-argument
@pytest.fixture(scope="module")
def load_test_data(
    django_db_setup: None, django_db_blocker: DjangoDbBlocker
) -> Iterator[None]:
    """
    Load the test data for the test cases of a module. The data is rolled back
    afterwards, so it doesn't leak into tests that expect an empty database.

    :param django_db_setup: The fixture providing the database availability
    :type django_db_setup: :fixture:`django_db_setup`

    :param django_db_blocker: The fixture providing the database blocker
    :type django_db_blocker: :fixture:`django_db_blocker`
    """
    with django_db_blocker.unblock(), transaction.atomic():
        call_command("loaddata", "test_data")
        yield
        transaction.set_rollback(True)


@pytest.fixture(name="logged_in_client")
def fixture_logged_in_client(db: None) -> Client:
    """
    A client that is logged in to the CMS as a staff user

    :param db: The fixture providing database access
    :type db: :fixture:`db`
    """
    user = get_user_model().objects.create_user(
        username="logged-in-tester", password="secret", is_staff=True
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def default_image_prompt(request: pytest.FixtureRequest) -> None:
    """
    Make sure the default image prompt, seeded by migration 0051, exists in
    every test that uses the database.

    ``transaction=True`` tests flush every table afterwards, rows created by
    migrations included, and image generation can't build a prompt without a
    default.

    :param request: The request of the test, to find out whether it uses the
        database
    :type request: :fixture:`request`
    """
    # pylint: disable=import-outside-toplevel
    from lunes_cms.cmsv2.models import ImagePrompt

    if request.node.get_closest_marker("django_db") is None:
        for fixture in ("db", "transactional_db"):
            if fixture in request.fixturenames:
                request.getfixturevalue(fixture)
                break
        else:
            return
    if not ImagePrompt.objects.filter(is_default=True).exists():
        ImagePrompt.objects.create(
            name=image_prompt_migration.INITIAL_PROMPT_NAME,
            prompt=image_prompt_migration.INITIAL_PROMPT,
            is_default=True,
        )
