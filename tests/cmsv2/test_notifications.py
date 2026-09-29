"""
Tests for the email notifications of experts (#650).

An expert of a unit is a user with a review assignment for a word of that
unit. Experts are told by email about units assigned to them, words added to
their units and new images of the words of their units.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest import mock

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import reverse
from pytest_django import Settings
from tablib import Dataset

from lunes_cms.cmsv2.admins.unit_admin import UnitAdmin
from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.admins.word_import_resource import import_words_from_csv
from lunes_cms.cmsv2.models import Job, Review, Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.notifications import (
    notify_image_added,
    notify_units_assigned,
    notify_words_added,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def base_url(settings: Settings, tmp_path: Path) -> None:
    settings.BASE_URL = "https://cms.example.com"
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture(autouse=True)
def run_on_commit() -> Generator[None, None, None]:
    """
    Notifications are sent on commit, which the transaction of a test never
    does, so send them right away instead.
    """
    with mock.patch(
        "lunes_cms.cmsv2.notifications.transaction.on_commit",
        side_effect=lambda callback: callback(),
    ):
        yield


@pytest.fixture
def expert() -> User:
    return get_user_model().objects.create_user(
        username="expert", email="expert@example.com", first_name="Erika"
    )


@pytest.fixture
def superuser() -> User:
    return get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="password"
    )


@pytest.fixture
def unit(expert: User) -> Unit:
    """A unit whose only word is under review by ``expert``"""
    unit = Unit.objects.create(title="Werkzeug")
    word = Word.objects.create(word="Hammer", singular_article=1)
    unit_word = UnitWordRelation.objects.create(unit=unit, word=word)
    Review.objects.create(unit_word=unit_word, reviewer=expert)
    return unit


def test_units_assigned_mail_lists_the_units(expert: User) -> None:
    unit = Unit.objects.create(title="Werkzeug")

    notify_units_assigned(expert, [unit, unit])

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["expert@example.com"]
    assert "Erika" in message.body
    assert message.body.count("Werkzeug") == 1
    review_url = reverse("expert_access:review")
    assert f"https://cms.example.com{review_url}" in message.body


def test_units_assigned_by_the_expert_themselves_send_no_mail(expert: User) -> None:
    notify_units_assigned(expert, [Unit.objects.create(title="A")], assigned_by=expert)

    assert not mail.outbox


def test_expert_without_email_gets_no_mail() -> None:
    expert = get_user_model().objects.create_user(username="no-mail")

    notify_units_assigned(expert, [Unit.objects.create(title="A")])

    assert not mail.outbox


def test_words_added_notify_only_the_experts_of_the_unit(
    unit: Unit, expert: User
) -> None:
    other_expert = get_user_model().objects.create_user(
        username="other", email="other@example.com"
    )
    other_unit = Unit.objects.create(title="Küche")
    other_relation = UnitWordRelation.objects.create(
        unit=other_unit, word=Word.objects.create(word="Topf", singular_article=1)
    )
    Review.objects.create(unit_word=other_relation, reviewer=other_expert)

    relation = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )
    notify_words_added([relation])

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Säge (Werkzeug)" in mail.outbox[0].body


def test_words_added_by_the_expert_themselves_send_no_mail(
    unit: Unit, expert: User
) -> None:
    relation = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )

    notify_words_added([relation], added_by=expert)

    assert not mail.outbox


def test_words_added_to_a_unit_without_experts_send_no_mail() -> None:
    relation = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="A"),
        word=Word.objects.create(word="Säge", singular_article=2),
    )

    notify_words_added([relation])

    assert not mail.outbox


def test_failing_mail_server_does_not_raise(unit: Unit) -> None:
    relation = unit.unit_word_relations.get()

    with mock.patch(
        "lunes_cms.cmsv2.notifications.send_mail", side_effect=OSError("down")
    ):
        notify_image_added(relation)


#
# Where the notifications are triggered
#


def _post_request(data: dict) -> HttpRequest:
    request = RequestFactory().post("/", data)
    request.session = {}  # type: ignore[assignment]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


def test_assign_to_user_notifies_the_expert(unit: Unit, superuser: User) -> None:
    new_expert = get_user_model().objects.create_user(
        username="new", email="new@example.com"
    )
    request = _post_request({"apply": "1", "user": new_expert.pk})
    request.user = superuser

    UnitAdmin(Unit, admin.site).assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    assert [message.to for message in mail.outbox] == [["new@example.com"]]
    assert "Werkzeug" in mail.outbox[0].body


def test_assign_to_user_sends_no_mail_when_nothing_is_new(
    unit: Unit, expert: User, superuser: User
) -> None:
    request = _post_request({"apply": "1", "user": expert.pk})
    request.user = superuser

    UnitAdmin(Unit, admin.site).assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    assert not mail.outbox


@pytest.mark.parametrize("admin_class", [UnitAdmin, WordAdmin])
def test_inline_words_notify_the_experts(
    admin_class: type[UnitAdmin | WordAdmin], unit: Unit, superuser: User
) -> None:
    relation = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )
    formset = mock.MagicMock(model=UnitWordRelation, new_objects=[relation])
    request = RequestFactory().post("/")
    request.user = superuser

    model_admin = admin_class(Unit if admin_class is UnitAdmin else Word, admin.site)
    model_admin.save_formset(request, mock.MagicMock(), formset, change=True)

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Säge (Werkzeug)" in mail.outbox[0].body


def test_csv_import_notifies_the_experts_once(unit: Unit, superuser: User) -> None:
    job = Job.objects.create(name="Handwerk")
    unit.jobs.add(job)
    dataset = Dataset(headers=["Einheit", "Vokabel", "Artikel"])
    dataset.append(["Werkzeug", "Säge", "die"])
    dataset.append(["Werkzeug", "Zange", "die"])

    import_words_from_csv(dataset, job, superuser)

    assert len(mail.outbox) == 1
    assert "Säge (Werkzeug)" in mail.outbox[0].body
    assert "Zange (Werkzeug)" in mail.outbox[0].body


def _image(name: str = "image.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"image", content_type="image/png")


@pytest.fixture
def skip_webp_conversion() -> Generator[None, None, None]:
    with mock.patch(
        "lunes_cms.cmsv2.models.unit.convert_image_to_webp", return_value=False
    ):
        yield


@pytest.mark.usefixtures("skip_webp_conversion")
def test_new_image_notifies_the_experts(unit: Unit) -> None:
    relation = unit.unit_word_relations.get()

    relation.image = _image()
    relation.save()

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Hammer (Werkzeug)" in mail.outbox[0].body


@pytest.mark.usefixtures("skip_webp_conversion")
def test_unchanged_or_removed_image_sends_no_mail(unit: Unit) -> None:
    relation = unit.unit_word_relations.get()
    relation.image = _image()
    relation.save()
    mail.outbox.clear()

    relation.example_sentence = "Der Hammer ist schwer."
    relation.save()
    relation.image = None
    relation.save()

    assert not mail.outbox


@pytest.mark.usefixtures("skip_webp_conversion")
def test_new_relation_with_image_sends_no_image_mail(unit: Unit) -> None:
    UnitWordRelation.objects.create(
        unit=unit,
        word=Word.objects.create(word="Säge", singular_article=2),
        image=_image(),
    )

    assert not mail.outbox
