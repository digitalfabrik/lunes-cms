"""
Shared fixtures for the cmsv2 tests.
"""

from collections.abc import Callable, Generator
from itertools import count
from unittest import mock

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.test import Client

from lunes_cms.cmsv2.models import Word


@pytest.fixture(autouse=True)
def bypass_audio_conversion() -> Generator[None, None, None]:
    """
    Word.save() runs ``convert_audio()`` (ffmpeg re-encodes the mp3) when an
    audio file is set. Tests feed dummy bytes through, so skip the conversion.
    """
    with mock.patch.object(Word, "convert_audio", lambda self: None):
        yield


@pytest.fixture
def client_with_permissions(db: None) -> Callable[..., Client]:
    """
    Build a client logged in as a user whose group grants exactly the given
    cmsv2 permissions, like the groups of the editors in production.
    """
    counter = count(1)

    def create(*codenames: str) -> Client:
        name = f"editor-{next(counter)}"
        group = Group.objects.create(name=f"group-of-{name}")
        group.permissions.set(
            Permission.objects.filter(
                content_type__app_label="cmsv2", codename__in=codenames
            )
        )
        user = User.objects.create_user(f"user-of-{name}")
        user.groups.add(group)
        client = Client()
        client.force_login(user)
        return client

    return create
