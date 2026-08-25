"""
Tests for the ``assign_to_user`` bulk action on UnitAdmin (#644).

Covers the refactor that moved review assignment from the Unit level to the
Word level: a word shared by several selected units must only be reviewed
once, already-assigned words must be skipped, and the action stays
superuser-only.
"""

from __future__ import annotations

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import RequestFactory

from lunes_cms.cmsv2.admins.unit_admin import UnitAdmin
from lunes_cms.cmsv2.models import Review, Unit, Word


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def unit_admin() -> UnitAdmin:
    return UnitAdmin(Unit, admin.site)


def _post_request(request_factory: RequestFactory, data: dict) -> HttpRequest:
    """Build a POST request with a working messages store for admin actions."""
    request = request_factory.post("/", data)
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


def test_assign_to_user_creates_one_review_per_word_across_units(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    """A word shared by several selected units must only get one Review
    (word-level), not one per unit (old unit-level behaviour)."""
    shared_word = Word.objects.create(word="Hammer", singular_article=1)
    unit_a = Unit.objects.create(title="Unit A")
    unit_b = Unit.objects.create(title="Unit B")
    unit_a.words.add(shared_word)
    unit_b.words.add(shared_word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = admin_user

    unit_admin.assign_to_user(
        request, Unit.objects.filter(pk__in=[unit_a.pk, unit_b.pk])
    )

    assert Review.objects.filter(word=shared_word, reviewer=target_user).count() == 1


def test_assign_to_user_skips_already_assigned_words(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Unit A")
    unit.words.add(word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )
    Review.objects.create(word=word, reviewer=target_user)

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = admin_user

    unit_admin.assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    assert Review.objects.filter(word=word, reviewer=target_user).count() == 1


def test_assign_to_user_sets_assigned_by_to_acting_admin(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Unit A")
    unit.words.add(word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = admin_user

    unit_admin.assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    review = Review.objects.get(word=word, reviewer=target_user)
    assert review.assigned_by == admin_user


def test_assign_to_user_denies_non_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    non_superuser = get_user_model().objects.create_user(
        username="staff", is_staff=True
    )

    request = _post_request(request_factory, {"apply": "1"})
    request.user = non_superuser

    with pytest.raises(PermissionDenied):
        unit_admin.assign_to_user(request, Unit.objects.none())


def test_assign_to_user_denies_anonymous_user(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    request = _post_request(request_factory, {"apply": "1"})
    request.user = AnonymousUser()

    with pytest.raises(PermissionDenied):
        unit_admin.assign_to_user(request, Unit.objects.none())
