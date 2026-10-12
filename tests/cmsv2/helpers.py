"""
Shared helpers for the cmsv2 tests.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.test import Client


class PermissionClient(Client):
    """
    A test client logged in as the given user, kept on ``client.user``.
    """

    def __init__(self, user: User, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.user = user
        self.force_login(user)
