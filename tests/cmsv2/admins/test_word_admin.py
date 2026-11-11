"""
Tests for the ``assign_to_user`` bulk action on WordAdmin.

Reviews are assigned per unit-word relation: a word of a single unit is
reviewed in that unit, a word of several units is reviewed in the unit chosen
for it, and a word of no unit is skipped. The action requires the
``can_assign_reviews`` permission and is limited to the area of the user.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpRequest
from django.test import RequestFactory

from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.models import Area, Review, Unit, UnitWordRelation, Word
from tests.cmsv2.helpers import PermissionClient


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def word_admin() -> WordAdmin:
    return WordAdmin(Word, admin.site)


def _post_request(request_factory: RequestFactory, data: dict) -> HttpRequest:
    """Build a POST request with a working messages store for admin actions."""
    request = request_factory.post("/", data)
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


def test_assign_to_user_reviews_a_word_in_its_only_unit(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit = Unit.objects.create(title="Unit A")
    unit_word = UnitWordRelation.objects.create(unit=unit, word=word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(
        request_factory,
        {"apply": "1", "user": target_user.pk, f"unit_word_{word.pk}": unit_word.pk},
    )
    request.user = admin_user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    review = Review.objects.get(reviewer=target_user)
    assert review.unit_word == unit_word
    assert review.assigned_by == admin_user


def test_assign_to_user_reviews_a_word_of_several_units_in_the_chosen_unit(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    UnitWordRelation.objects.create(unit=Unit.objects.create(title="Unit A"), word=word)
    chosen_unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit B"), word=word
    )
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(
        request_factory,
        {
            "apply": "1",
            "user": target_user.pk,
            f"unit_word_{word.pk}": chosen_unit_word.pk,
        },
    )
    request.user = admin_user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    review = Review.objects.get(reviewer=target_user)
    assert review.unit_word == chosen_unit_word


def test_assign_to_user_falls_back_to_one_of_the_units_without_a_unit_choice(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    Unit.objects.create(title="Unit A").words.add(word)
    Unit.objects.create(title="Unit B").words.add(word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = admin_user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    review = Review.objects.get(reviewer=target_user)
    assert review.unit_word.word == word


def test_assign_to_user_assigns_the_posted_unit_word(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    other_word = Word.objects.create(word="Zange", singular_article=2)
    unit_a = Unit.objects.create(title="Unit A")
    unit_a.words.add(word)
    Unit.objects.create(title="Unit B").words.add(word)
    other_unit_word = UnitWordRelation.objects.create(unit=unit_a, word=other_word)
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(
        request_factory,
        {
            "apply": "1",
            "user": target_user.pk,
            f"unit_word_{word.pk}": other_unit_word.pk,
        },
    )
    request.user = admin_user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    review = Review.objects.get(reviewer=target_user)
    assert review.unit_word == other_unit_word


def test_assign_to_user_skips_words_without_unit(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    word_without_unit = Word.objects.create(word="Zange", singular_article=2)
    unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit A"), word=word
    )
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    request = _post_request(
        request_factory,
        {"apply": "1", "user": target_user.pk, f"unit_word_{word.pk}": unit_word.pk},
    )
    request.user = admin_user

    word_admin.assign_to_user(
        request, Word.objects.filter(pk__in=[word.pk, word_without_unit.pk])
    )

    assert list(
        Review.objects.filter(reviewer=target_user).values_list(
            "unit_word__word", flat=True
        )
    ) == [word.pk]


def test_assign_to_user_skips_already_assigned_unit_words(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit A"), word=word
    )
    target_user = get_user_model().objects.create_user(username="reviewer")
    admin_user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )
    Review.objects.create(unit_word=unit_word, reviewer=target_user)

    request = _post_request(
        request_factory,
        {"apply": "1", "user": target_user.pk, f"unit_word_{word.pk}": unit_word.pk},
    )
    request.user = admin_user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    assert Review.objects.filter(unit_word=unit_word, reviewer=target_user).count() == 1


def test_assign_to_user_is_hidden_from_an_anonymous_user(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    request.user = AnonymousUser()

    assert "assign_to_user" not in word_admin.get_actions(request)


def test_assign_to_user_is_hidden_from_a_non_superuser(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    request.user = get_user_model().objects.create_user(username="editor")

    assert "assign_to_user" not in word_admin.get_actions(request)


def test_assign_to_user_is_offered_to_a_superuser(
    db: None, word_admin: WordAdmin, request_factory: RequestFactory
) -> None:
    request = request_factory.get("/")
    request.user = get_user_model().objects.create_superuser(
        username="admin", password="password"
    )

    assert "assign_to_user" in word_admin.get_actions(request)


def test_assign_to_user_is_offered_to_a_user_who_may_assign(
    word_admin: WordAdmin,
    request_factory: RequestFactory,
    client_with_permissions: Callable[..., PermissionClient],
) -> None:
    request = request_factory.get("/")
    request.user = client_with_permissions("can_assign_reviews").user

    assert "assign_to_user" in word_admin.get_actions(request)


def test_assign_to_user_ignores_a_posted_unit_word_of_another_area(
    word_admin: WordAdmin,
    request_factory: RequestFactory,
    client_with_permissions: Callable[..., PermissionClient],
    main_app_area: Area,
) -> None:
    other_area = Area.objects.create(name="Area B")
    word = Word.objects.create(word="Hammer", singular_article=1, area=main_app_area)
    UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit A", area=main_app_area), word=word
    )
    foreign_unit_word = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit B", area=other_area),
        word=Word.objects.create(word="Zange", singular_article=2, area=other_area),
    )
    target_user = get_user_model().objects.create_user(username="reviewer")

    request = _post_request(
        request_factory,
        {
            "apply": "1",
            "user": target_user.pk,
            f"unit_word_{word.pk}": foreign_unit_word.pk,
        },
    )
    request.user = client_with_permissions("can_assign_reviews").user

    word_admin.assign_to_user(request, Word.objects.filter(pk=word.pk))

    assert not Review.objects.exists()


def test_assign_to_user_skips_words_of_another_area(
    word_admin: WordAdmin,
    request_factory: RequestFactory,
    client_with_permissions: Callable[..., PermissionClient],
) -> None:
    other_area = Area.objects.create(name="Area B")
    foreign_word = Word.objects.create(
        word="Zange", singular_article=2, area=other_area
    )
    UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="Unit B", area=other_area), word=foreign_word
    )
    target_user = get_user_model().objects.create_user(username="reviewer")

    request = _post_request(request_factory, {"apply": "1", "user": target_user.pk})
    request.user = client_with_permissions("can_assign_reviews").user

    word_admin.assign_to_user(request, Word.objects.filter(pk=foreign_word.pk))

    assert not Review.objects.exists()
