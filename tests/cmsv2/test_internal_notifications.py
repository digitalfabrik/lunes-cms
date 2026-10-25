"""
Tests for the internal notifications of staff about the review work of
experts (#1038).
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.core.management import call_command
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone
from pytest_django import Settings

from lunes_cms.cmsv2.internal_notifications import (
    notify_review_submitted,
    notify_slow_experts,
)
from lunes_cms.cmsv2.models import Notification, Review, Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.models.static import NotificationType, ReviewStatus
from lunes_cms.core.context_processors import notification_processor

pytestmark = pytest.mark.django_db

NOTIFICATIONS_URL = "/en/admin/cmsv2/notification/"


@pytest.fixture(autouse=True)
def thresholds(settings: Settings) -> None:
    settings.REVIEW_REJECTION_ALERT_THRESHOLD = 2
    settings.REVIEW_SLOW_EXPERT_DAYS = 14


@pytest.fixture
def staff() -> User:
    return User.objects.create_user(username="staff", is_staff=True)


@pytest.fixture
def expert() -> User:
    expert = User.objects.create_user(
        username="expert", first_name="Erika", last_name="Muster"
    )
    expert.user_permissions.add(Permission.objects.get(codename="can_review"))
    return expert


@pytest.fixture
def unit() -> Unit:
    return Unit.objects.create(title="Werkzeug")


def assign(
    unit: Unit, expert: User, assigned_by: User | None, count: int
) -> list[Review]:
    """Assign ``count`` new words of ``unit`` to ``expert`` for review"""
    reviews = []
    for index in range(count):
        word = Word.objects.create(word=f"Wort {unit.pk}-{index}", singular_article=1)
        unit_word = UnitWordRelation.objects.create(unit=unit, word=word)
        reviews.append(
            Review.objects.create(
                unit_word=unit_word, reviewer=expert, assigned_by=assigned_by
            )
        )
    return reviews


def submit(review: Review, status: str) -> None:
    review.review_status = status
    review.save()
    notify_review_submitted(review)


def notifications_of(user: User) -> list[str]:
    return list(
        Notification.objects.filter(recipient=user).values_list(
            "notification_type", flat=True
        )
    )


def test_completing_a_unit_notifies_the_assigning_staff(
    unit: Unit, expert: User, staff: User
) -> None:
    first, second = assign(unit, expert, staff, 2)

    submit(first, ReviewStatus.APPROVED)
    assert not Notification.objects.exists()

    submit(second, ReviewStatus.APPROVED)
    notification = Notification.objects.get()
    assert notification.recipient == staff
    assert notification.notification_type == NotificationType.REVIEW_COMPLETED
    assert notification.unit == unit
    assert not notification.is_read
    assert notification.message == "Erika Muster has finished the review of Werkzeug."


def test_completion_is_tracked_per_unit(unit: Unit, expert: User, staff: User) -> None:
    (review,) = assign(unit, expert, staff, 1)
    assign(Unit.objects.create(title="Küche"), expert, staff, 1)

    submit(review, ReviewStatus.APPROVED)

    assert Notification.objects.get().unit == unit


def test_reviews_without_assigning_user_notify_superusers(
    unit: Unit, expert: User
) -> None:
    User.objects.create_superuser(username="admin")
    User.objects.create_superuser(username="inactive", is_active=False)
    User.objects.create_user(username="not-a-superuser")
    (review,) = assign(unit, expert, None, 1)

    submit(review, ReviewStatus.APPROVED)

    active_superusers = User.objects.filter(is_superuser=True, is_active=True)
    assert set(Notification.objects.values_list("recipient", flat=True)) == set(
        active_superusers.values_list("pk", flat=True)
    )


def test_every_recipient_gets_an_own_notification(
    unit: Unit, expert: User, staff: User
) -> None:
    other_staff = User.objects.create_user(username="other-staff")
    first = assign(unit, expert, staff, 1)[0]
    second = assign(unit, expert, other_staff, 1)[0]

    submit(first, ReviewStatus.APPROVED)
    submit(second, ReviewStatus.APPROVED)

    assert notifications_of(staff) == [NotificationType.REVIEW_COMPLETED]
    assert notifications_of(other_staff) == [NotificationType.REVIEW_COMPLETED]


def test_expert_who_assigned_reviews_to_themselves_is_not_notified(
    unit: Unit, expert: User
) -> None:
    (review,) = assign(unit, expert, expert, 1)

    submit(review, ReviewStatus.APPROVED)

    assert not Notification.objects.exists()


def test_many_flagged_words_notify_staff_once(
    unit: Unit, expert: User, staff: User
) -> None:
    reviews = assign(unit, expert, staff, 5)

    submit(reviews[0], ReviewStatus.REJECTED)
    submit(reviews[1], ReviewStatus.CANNOT_BE_ASSESSED)
    assert not Notification.objects.exists()

    submit(reviews[2], ReviewStatus.CHANGE_REQUESTED)
    notification = Notification.objects.get()
    assert notification.notification_type == NotificationType.MANY_REJECTIONS
    assert notification.count == 2
    assert (
        notification.message == "Erika Muster has flagged 2 words of Werkzeug as wrong."
    )

    submit(reviews[3], ReviewStatus.REJECTED)
    assert Notification.objects.count() == 1


def test_last_flagged_word_notifies_about_rejections_and_completion(
    unit: Unit, expert: User, staff: User
) -> None:
    first, second = assign(unit, expert, staff, 2)

    submit(first, ReviewStatus.REJECTED)
    submit(second, ReviewStatus.REJECTED)

    assert sorted(notifications_of(staff)) == [
        NotificationType.MANY_REJECTIONS,
        NotificationType.REVIEW_COMPLETED,
    ]


def test_submitting_in_the_expert_view_notifies_staff(
    unit: Unit, expert: User, staff: User
) -> None:
    (review,) = assign(unit, expert, staff, 1)
    client = Client()
    client.force_login(expert)

    response = client.post(
        reverse("expert_access:review"),
        {"review_id": review.pk, "review_status": ReviewStatus.APPROVED},
    )

    assert response.status_code == 302
    assert notifications_of(staff) == [NotificationType.REVIEW_COMPLETED]


def test_skipping_in_the_expert_view_does_not_notify(
    unit: Unit, expert: User, staff: User
) -> None:
    (review,) = assign(unit, expert, staff, 1)
    client = Client()
    client.force_login(expert)

    client.post(reverse("expert_access:review"), {"review_id": review.pk, "skip": "1"})

    assert not Notification.objects.exists()


def test_slow_experts_are_reported_once_per_period(
    unit: Unit, expert: User, staff: User
) -> None:
    old, approved, recent = assign(unit, expert, staff, 3)
    Review.objects.filter(pk__in=[old.pk, approved.pk]).update(
        assigned_at=timezone.now() - timedelta(days=15)
    )
    submit(approved, ReviewStatus.APPROVED)

    (notification,) = notify_slow_experts()
    assert notification.recipient == staff
    assert notification.notification_type == NotificationType.SLOW_EXPERT
    assert notification.count == 1
    assert notification.unit is None
    assert notification.message == (
        "Erika Muster has 1 reviews which are pending for more than 14 days."
    )
    assert not notify_slow_experts()

    Notification.objects.update(created_at=timezone.now() - timedelta(days=15))
    assert len(notify_slow_experts()) == 1
    assert recent.review_status == ReviewStatus.PENDING


def test_experts_without_overdue_reviews_are_not_reported(
    unit: Unit, expert: User, staff: User
) -> None:
    assign(unit, expert, staff, 1)

    assert not notify_slow_experts()


def test_notify_slow_experts_command(unit: Unit, expert: User, staff: User) -> None:
    assign(unit, expert, staff, 2)
    Review.objects.update(assigned_at=timezone.now() - timedelta(days=30))
    out = StringIO()

    call_command("notify_slow_experts", stdout=out)

    assert "Created 1 notification(s)" in out.getvalue()
    assert Notification.objects.get().count == 2


def test_message_of_notification_about_deleted_unit(
    unit: Unit, expert: User, staff: User
) -> None:
    (review,) = assign(unit, expert, staff, 1)
    submit(review, ReviewStatus.APPROVED)

    unit.delete()

    assert Notification.objects.get().message == (
        "Erika Muster has finished the review of a deleted unit."
    )


@pytest.fixture
def notifications(unit: Unit, expert: User, staff: User) -> list[Notification]:
    other = User.objects.create_superuser(username="other")
    return [
        Notification.objects.create(
            recipient=recipient,
            notification_type=NotificationType.REVIEW_COMPLETED,
            expert=expert,
            unit=unit,
        )
        for recipient in (staff, staff, other)
    ]


def test_admin_lists_only_own_notifications(
    notifications: list[Notification], staff: User
) -> None:
    client = Client()
    client.force_login(staff)

    response = client.get(NOTIFICATIONS_URL)

    assert response.status_code == 200
    assert [n.pk for n in response.context["cl"].result_list] == [
        n.pk for n in reversed(notifications[:2])
    ]
    other = client.get(f"{NOTIFICATIONS_URL}{notifications[2].pk}/change/")
    assert other.status_code == 302


def test_admin_actions_mark_notifications_as_read_and_unread(
    notifications: list[Notification], staff: User
) -> None:
    client = Client()
    client.force_login(staff)
    own = [n.pk for n in notifications]

    client.post(NOTIFICATIONS_URL, {"action": "mark_as_read", "_selected_action": own})
    read = Notification.objects.exclude(read_at=None)
    assert sorted(read.values_list("pk", flat=True)) == own[:2]

    unread_filter = client.get(NOTIFICATIONS_URL, {"read": "no"})
    assert not unread_filter.context["cl"].result_list

    client.post(
        NOTIFICATIONS_URL, {"action": "mark_as_unread", "_selected_action": own}
    )
    assert not Notification.objects.exclude(read_at=None).exists()


def test_opening_a_notification_marks_it_as_read(
    notifications: list[Notification], staff: User
) -> None:
    client = Client()
    client.force_login(staff)

    response = client.get(f"{NOTIFICATIONS_URL}{notifications[0].pk}/change/")

    assert response.status_code == 200
    notifications[0].refresh_from_db()
    assert notifications[0].is_read


def test_context_processor_counts_unread_notifications(
    notifications: list[Notification], staff: User
) -> None:
    request = RequestFactory().get("/")
    request.user = staff
    notifications[0].read_at = timezone.now()
    notifications[0].save()

    assert notification_processor(request) == {"unread_notification_count": 1}


def test_context_processor_for_anonymous_users() -> None:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    assert notification_processor(request) == {"unread_notification_count": 0}
