"""
Internal notifications for staff about the review work of experts, see #1038.

Unlike the emails in :mod:`~lunes_cms.cmsv2.notifications`, these are stored
as :class:`~lunes_cms.cmsv2.models.notification.Notification` rows, one per
recipient, and shown in the admin until the recipient marks them as read.

Staff is told

* when an expert has finished the review of a unit,
* when an expert has rejected or requested changes for many words of a unit
  (:attr:`~lunes_cms.core.settings.REVIEW_REJECTION_ALERT_THRESHOLD`),
* when an expert has reviews which are pending for too long
  (:attr:`~lunes_cms.core.settings.REVIEW_SLOW_EXPERT_DAYS`), checked by the
  ``notify_slow_experts`` management command.

The recipients are the users who assigned the reviews in question. Reviews
whose assigning user is unknown (e.g. deleted) are reported to all
superusers instead.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, QuerySet
from django.utils import timezone

from .models import Notification, Review
from .models.static import NotificationType, ReviewStatus

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from .models import Unit

#: The review states which flag a word as wrong
FLAGGED_REVIEW_STATUSES = [ReviewStatus.REJECTED, ReviewStatus.CHANGE_REQUESTED]


def staff_to_notify(expert: User, reviews: QuerySet[Review]) -> QuerySet[User]:
    """
    Find the staff to notify about the given reviews of an expert.

    Args:
        expert: The expert the reviews belong to, never notified themselves
        reviews: The reviews the notification is about

    Returns:
        QuerySet: The users who assigned the reviews, plus all superusers if
        the assigning user of any of them is unknown
    """
    users = get_user_model().objects.filter(is_active=True).exclude(pk=expert.pk)
    staff = users.filter(created_review_assignments__in=reviews)
    if reviews.filter(assigned_by=None).exists():
        staff = staff | users.filter(is_superuser=True)
    return staff.distinct()


def notify_staff(
    expert: User,
    reviews: QuerySet[Review],
    notification_type: NotificationType,
    unit: Unit | None = None,
    count: int = 0,
) -> list[Notification]:
    """
    Create a notification for every staff member responsible for the reviews.

    Args:
        expert: The expert the notification is about
        reviews: The reviews the notification is about
        notification_type: The type of the notification
        unit: The unit the notification is about, if any
        count: The number of flagged or overdue reviews

    Returns:
        list: The created notifications
    """
    return Notification.objects.bulk_create(
        Notification(
            recipient=recipient,
            notification_type=notification_type,
            expert=expert,
            unit=unit,
            count=count,
        )
        for recipient in staff_to_notify(expert, reviews)
    )


def notify_review_submitted(review: Review) -> None:
    """
    Notify staff about a review an expert has just submitted, if the review
    completes the unit or the expert has flagged many words of it.

    Args:
        review: The submitted review
    """
    if review.review_status == ReviewStatus.PENDING:
        return
    expert = review.reviewer
    unit = review.unit_word.unit
    reviews_of_unit = Review.objects.filter(reviewer=expert, unit_word__unit=unit)

    if review.review_status in FLAGGED_REVIEW_STATUSES:
        flagged = reviews_of_unit.filter(review_status__in=FLAGGED_REVIEW_STATUSES)
        flagged_count = flagged.count()
        already_notified = Notification.objects.filter(
            notification_type=NotificationType.MANY_REJECTIONS,
            expert=expert,
            unit=unit,
        ).exists()
        if (
            flagged_count >= settings.REVIEW_REJECTION_ALERT_THRESHOLD
            and not already_notified
        ):
            notify_staff(
                expert,
                flagged,
                NotificationType.MANY_REJECTIONS,
                unit=unit,
                count=flagged_count,
            )

    if not reviews_of_unit.filter(review_status=ReviewStatus.PENDING).exists():
        notify_staff(
            expert, reviews_of_unit, NotificationType.REVIEW_COMPLETED, unit=unit
        )


def notify_slow_experts() -> list[Notification]:
    """
    Notify staff about experts with reviews which are pending for more than
    :attr:`~lunes_cms.core.settings.REVIEW_SLOW_EXPERT_DAYS` days.

    An expert is reported at most once in that period, so the check can run
    daily without repeating the same notification every day.

    Returns:
        list: The created notifications
    """
    cutoff = timezone.now() - timedelta(days=settings.REVIEW_SLOW_EXPERT_DAYS)
    overdue = Review.objects.filter(
        review_status=ReviewStatus.PENDING, assigned_at__lt=cutoff
    )
    recently_notified = Notification.objects.filter(
        notification_type=NotificationType.SLOW_EXPERT, created_at__gte=cutoff
    ).values("expert")
    experts = (
        get_user_model()
        .objects.filter(review_assignments__in=overdue)
        .exclude(pk__in=recently_notified)
        .annotate(overdue_count=Count("review_assignments"))
    )
    notifications = []
    for expert in experts:
        notifications += notify_staff(
            expert,
            overdue.filter(reviewer=expert),
            NotificationType.SLOW_EXPERT,
            count=expert.overdue_count,
        )
    return notifications
