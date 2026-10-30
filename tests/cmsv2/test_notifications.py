"""
Tests for the email notifications of experts (#650, #1094).

An expert of a unit is a user with a review assignment for a word of that
unit. Experts are told about units assigned to them, words added to their
units and new images of the words of their units in one digest per run of
``send_expert_digest``.
"""

from __future__ import annotations

from collections.abc import Generator
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import reverse
from django.utils import translation
from pytest_django import Settings
from tablib import Dataset

from lunes_cms.cmsv2.admins.unit_admin import UnitAdmin
from lunes_cms.cmsv2.admins.word_admin import WordAdmin
from lunes_cms.cmsv2.admins.word_import_resource import import_words_from_csv
from lunes_cms.cmsv2.models import (
    Job,
    PendingNotification,
    Review,
    Unit,
    UnitWordRelation,
    Word,
)
from lunes_cms.cmsv2.notifications import (
    notify_image_added,
    notify_units_assigned,
    notify_words_added,
    send_digests,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def base_url(settings: Settings, tmp_path: Path) -> None:
    settings.BASE_URL = "https://cms.example.com"
    settings.MEDIA_ROOT = str(tmp_path)


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


def test_units_assigned_mail_lists_the_units(unit: Unit, expert: User) -> None:
    notify_units_assigned(expert, [unit, unit])

    send_digests()

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["expert@example.com"]
    assert "Erika" in message.body
    assert message.body.count("Werkzeug") == 1
    review_url = reverse("expert_access:review")
    assert f"https://cms.example.com{review_url}" in message.body


def test_units_assigned_by_the_expert_themselves_send_no_mail(expert: User) -> None:
    notify_units_assigned(expert, [Unit.objects.create(title="A")], assigned_by=expert)

    send_digests()

    assert not mail.outbox


def test_expert_without_email_gets_no_mail() -> None:
    expert = get_user_model().objects.create_user(username="no-mail")

    notify_units_assigned(expert, [Unit.objects.create(title="A")])

    send_digests()

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

    send_digests()

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Säge (Werkzeug)" in mail.outbox[0].body


def test_words_added_by_the_expert_themselves_send_no_mail(
    unit: Unit, expert: User
) -> None:
    relation = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )

    notify_words_added([relation], added_by=expert)

    send_digests()

    assert not mail.outbox


def test_words_added_to_a_unit_without_experts_send_no_mail() -> None:
    relation = UnitWordRelation.objects.create(
        unit=Unit.objects.create(title="A"),
        word=Word.objects.create(word="Säge", singular_article=2),
    )

    notify_words_added([relation])

    send_digests()

    assert not mail.outbox


def test_failing_mail_server_keeps_the_notifications(unit: Unit) -> None:
    notify_image_added(unit.unit_word_relations.get())

    with mock.patch(
        "lunes_cms.cmsv2.notifications.send_mail", side_effect=OSError("down")
    ):
        assert send_digests() == 0

    assert PendingNotification.objects.count() == 1
    assert send_digests() == 1
    assert not PendingNotification.objects.exists()


def test_digest_groups_all_notifications_in_one_mail(unit: Unit, expert: User) -> None:
    hammer = unit.unit_word_relations.get()
    saw = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )
    notify_units_assigned(expert, [unit])
    notify_words_added([saw])
    notify_words_added([saw])
    notify_image_added(hammer)
    notify_image_added(hammer)
    notify_image_added(saw)

    assert send_digests() == 1

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "New content to review"
    body = message.body
    assert body.index("assigned to you") < body.index("Werkzeug")
    assert body.index("were added to units") < body.index("Säge (Werkzeug)")
    assert body.index("New images") < body.index("Hammer (Werkzeug)")
    # Listed once each, the image of the new word not at all
    assert body.count("Säge (Werkzeug)") == 1
    assert body.count("Hammer (Werkzeug)") == 1
    assert not PendingNotification.objects.exists()


def test_digest_is_sent_only_once(unit: Unit) -> None:
    notify_image_added(unit.unit_word_relations.get())

    assert send_digests() == 1
    assert send_digests() == 0
    assert len(mail.outbox) == 1


def test_digest_drops_deleted_content(unit: Unit, expert: User) -> None:
    relation = UnitWordRelation.objects.create(
        unit=unit, word=Word.objects.create(word="Säge", singular_article=2)
    )
    notify_words_added([relation])
    relation.word.delete()

    assert send_digests() == 0
    assert not mail.outbox
    assert not PendingNotification.objects.exists()


def test_digest_drops_units_the_expert_no_longer_reviews(
    unit: Unit, expert: User
) -> None:
    notify_units_assigned(expert, [unit])
    Review.objects.filter(reviewer=expert).delete()

    assert send_digests() == 0
    assert not mail.outbox
    assert not PendingNotification.objects.exists()


def test_digest_is_sent_in_the_given_language() -> None:
    # Checks the active language instead of the German text, so the test does
    # not depend on compiled translation catalogs being present.
    languages: list[str | None] = []

    def fake_send_digests() -> int:
        languages.append(translation.get_language())
        return 0

    with mock.patch(
        "lunes_cms.cmsv2.management.commands.send_expert_digest.send_digests",
        side_effect=fake_send_digests,
    ):
        call_command("send_expert_digest", "--language", "de", stdout=StringIO())

    assert languages == ["de"]


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

    send_digests()

    assert [message.to for message in mail.outbox] == [["new@example.com"]]
    assert "Werkzeug" in mail.outbox[0].body


def test_assign_to_user_sends_no_mail_when_nothing_is_new(
    unit: Unit, expert: User, superuser: User
) -> None:
    request = _post_request({"apply": "1", "user": expert.pk})
    request.user = superuser

    UnitAdmin(Unit, admin.site).assign_to_user(request, Unit.objects.filter(pk=unit.pk))

    send_digests()

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

    send_digests()

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Säge (Werkzeug)" in mail.outbox[0].body


def test_csv_import_notifies_the_experts_once(unit: Unit, superuser: User) -> None:
    job = Job.objects.create(name="Handwerk")
    unit.jobs.add(job)
    dataset = Dataset(headers=["Einheit", "Vokabel", "Artikel"])
    dataset.append(["Werkzeug", "Säge", "die"])
    dataset.append(["Werkzeug", "Zange", "die"])

    import_words_from_csv(dataset, job, superuser)

    send_digests()

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

    send_digests()

    assert [message.to for message in mail.outbox] == [["expert@example.com"]]
    assert "Hammer (Werkzeug)" in mail.outbox[0].body


@pytest.mark.usefixtures("skip_webp_conversion")
def test_unchanged_or_removed_image_sends_no_mail(unit: Unit) -> None:
    relation = unit.unit_word_relations.get()
    relation.image = _image()
    relation.save()
    send_digests()
    mail.outbox.clear()

    relation.example_sentence = "Der Hammer ist schwer."
    relation.save()
    relation.image = None
    relation.save()

    send_digests()

    assert not mail.outbox


@pytest.mark.usefixtures("skip_webp_conversion")
def test_new_relation_with_image_sends_no_image_mail(unit: Unit) -> None:
    UnitWordRelation.objects.create(
        unit=unit,
        word=Word.objects.create(word="Säge", singular_article=2),
        image=_image(),
    )

    send_digests()

    assert not mail.outbox
