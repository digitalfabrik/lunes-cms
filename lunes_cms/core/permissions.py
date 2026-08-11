"""
Central module for custom permission checks across all apps. Add new
permission helper functions here as the project grows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser


def can_view_duplicates(user: "AbstractUser | AnonymousUser") -> bool:
    """
    Return True for superusers and users with the ``can_view_duplicates``
    permission (issue #531). Gates both the "Open duplicates" and "Accepted
    duplicates" analysis pages, the create-time duplicate-check warning, and
    accepting/undoing a duplicate as intentional - the whole
    duplicate-vocabulary feature set behind a single, group-assignable
    permission (see ``analysis.DuplicatedVocabulary.Meta.permissions``).
    """
    return user.has_perm("analysis.can_view_duplicates")
