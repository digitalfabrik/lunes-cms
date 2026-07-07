"""
This module contains shared fixtures for pytest
"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from pytest_django.plugin import DjangoDbBlocker


# pylint: disable=unused-argument
@pytest.fixture(scope="session")
def load_test_data(django_db_setup: None, django_db_blocker: DjangoDbBlocker) -> None:
    """
    Load the test data initially for all test cases

    :param django_db_setup: The fixture providing the database availability
    :type django_db_setup: :fixture:`django_db_setup`

    :param django_db_blocker: The fixture providing the database blocker
    :type django_db_blocker: :fixture:`django_db_blocker`
    """
    with django_db_blocker.unblock():
        call_command("loaddata", "test_data")
