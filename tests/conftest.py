"""
This module contains shared fixtures for pytest
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import Client
from pytest_django.plugin import DjangoDbBlocker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lunes_cms.cmsv2.models import ImagePrompt

#: The migration that creates the first image prompt, a prompt without
#: show-people variants.
image_prompt_migration = importlib.import_module(
    "lunes_cms.cmsv2.migrations.0053_imageprompt"
)

#: The migration that adds the prompt with show-people variants and makes it
#: the default (#1147).
show_people_prompt_migration = importlib.import_module(
    "lunes_cms.cmsv2.migrations.0055_show_people_image_prompt"
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
    Make sure the image prompts seeded by migrations 0053 and 0055 exist in
    every test that uses the database, the one with show-people variants as
    the default.

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
    if ImagePrompt.objects.filter(is_default=True).exists():
        return
    ImagePrompt.objects.get_or_create(
        name=image_prompt_migration.INITIAL_PROMPT_NAME,
        defaults={"prompt": image_prompt_migration.INITIAL_PROMPT},
    )
    ImagePrompt.objects.create(
        name=show_people_prompt_migration.PROMPT_NAME,
        supports_show_people=True,
        prompt_with_people=show_people_prompt_migration.PROMPT_WITH_PEOPLE,
        prompt_without_people=show_people_prompt_migration.PROMPT_WITHOUT_PEOPLE,
        is_default=True,
    )


@pytest.fixture
def prompt_without_variants(default_image_prompt: None) -> ImagePrompt:
    """
    Make the prompt without show-people variants that migration 0053 created
    the default, for tests of prompts that never classify.

    :param default_image_prompt: The fixture seeding the image prompts
    :type default_image_prompt: :fixture:`default_image_prompt`
    """
    # pylint: disable=import-outside-toplevel
    from lunes_cms.cmsv2.models import ImagePrompt

    prompt = ImagePrompt.objects.get(name=image_prompt_migration.INITIAL_PROMPT_NAME)
    prompt.is_default = True
    prompt.save()
    return prompt
