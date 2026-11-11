"""
Who may use the Bildschatz website and its word search.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser


def may_use_bildschatz(user: AbstractBaseUser | AnonymousUser) -> bool:
    """
    Whether the given user may use Bildschatz.

    Until Bildschatz is released to the public, only users who are logged in to
    the CMS may use it. This is the one place to change when it goes public.

    :param user: The user in question
    :return: Whether the user may use Bildschatz
    """
    return user.is_authenticated
