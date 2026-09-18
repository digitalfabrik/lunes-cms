"""
Tests for the ``assign_to_user`` bulk action on UnitAdmin (#644).

Covers the refactor that moved review assignment from the Unit level to the
unit-word level: a word shared by several selected units is reviewed once per
unit it belongs to, already-assigned unit-word relations must be skipped, and
the action stays superuser-only.
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
from lunes_cms.cmsv2.models import Review, Unit, UnitWordRelation, Word


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


def test_assign_to_user_creates_one_review_per_unit_word_relation(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    """A word shared by several selected units gets one Review per unit, because
    reviews are assigned per unit-word relation."""
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

    assert (
        Review.objects.filter(unit_word__word=shared_word, reviewer=target_user).count()
        == 2
    )


def test_assign_to_user_skips_already_assigned_unit_words(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Unit A")
    unit_word = UnitWordRelation.objects.create(unit=unit, word=word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )
    Review.objects.create(unit_word=unit_word, reviewer=target_user)

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = admin_user

    unit_admin.assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    assert Review.objects.filter(unit_word=unit_word, reviewer=target_user).count() == 1


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

    review = Review.objects.get(unit_word__word=word, reviewer=target_user)
    assert review.assigned_by == admin_user


def test_assign_to_user_denies_non_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    non_superuser = get_user_model().objects.create_user(username="editor")

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


#
# ``bulk_release`` and the dropdown of bulk actions (#1023 follow-up): both
# "Release all selected units" and "Assign selected units to user" act across
# areas and are meant for superusers only, not just in their own body but
# already hidden from the action dropdown for anybody else.
#


def test_bulk_release_denies_a_non_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    unit = Unit.objects.create(title="Unit A", released=False)
    editor = get_user_model().objects.create_user(username="editor")

    request = _post_request(request_factory, {})
    request.user = editor

    with pytest.raises(PermissionDenied):
        unit_admin.bulk_release(request, Unit.objects.filter(pk=unit.pk))

    unit.refresh_from_db()
    assert unit.released is False


def test_bulk_release_allows_a_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    unit = Unit.objects.create(title="Unit A", released=False)
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(request_factory, {})
    request.user = admin_user

    unit_admin.bulk_release(request, Unit.objects.filter(pk=unit.pk))

    unit.refresh_from_db()
    assert unit.released is True


def test_bulk_release_skips_already_released_units(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    released = Unit.objects.create(title="Unit A", released=True)
    draft = Unit.objects.create(title="Unit B", released=False)
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(request_factory, {})
    request.user = admin_user

    unit_admin.bulk_release(
        request, Unit.objects.filter(pk__in=[released.pk, draft.pk])
    )

    draft.refresh_from_db()
    assert draft.released is True


def test_bulk_actions_are_hidden_from_a_non_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    editor = get_user_model().objects.create_user(username="editor")
    request = request_factory.get("/")
    request.user = editor

    actions = unit_admin.get_actions(request)

    assert "bulk_release" not in actions
    assert "assign_to_user" not in actions


def test_bulk_actions_are_offered_to_a_superuser(
    db: None, unit_admin: UnitAdmin, request_factory: RequestFactory
) -> None:
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )
    request = request_factory.get("/")
    request.user = admin_user

    actions = unit_admin.get_actions(request)

    assert "bulk_release" in actions
    assert "assign_to_user" in actions
