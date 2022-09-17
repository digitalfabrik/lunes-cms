"""
This module contains shared fixtures for pytest
"""
import pytest

from django.core.management import call_command


# pylint: disable=unused-argument
@pytest.fixture(autouse=True, scope="session")
def load_test_data(django_db_setup, django_db_blocker):
    """
    Load the test data initially for all test cases

    :param django_db_setup: The fixture providing the database availability
    :type django_db_setup: :fixture:`django_db_setup`

    :param django_db_blocker: The fixture providing the database blocker
    :type django_db_blocker: :fixture:`django_db_blocker`
    """
    with django_db_blocker.unblock():
        call_command("loaddata", "test_data")
