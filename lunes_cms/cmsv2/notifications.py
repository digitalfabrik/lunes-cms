"""
Email notifications for experts, see #650 and #1094.

An expert of a unit is a user who has been assigned words of that unit for
review (see :class:`~lunes_cms.cmsv2.models.review.Review`). Experts are told by
email when there is new content for them to review:

* units were assigned to them,
* words were added to a unit they review,
* an image was uploaded or generated for a word of a unit they review.

The new content is not announced right away but stored as a
:class:`~lunes_cms.cmsv2.models.pending_notification.PendingNotification`, in
the same transaction as the change, so nothing is announced that is rolled back
afterwards. The ``send_expert_digest`` command, run weekly via cron, sends every
expert one email with all of it (see :func:`send_digests`).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable, TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from .models.pending_notification import NotificationType, PendingNotification
from .models.review import Review

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser, User

    # Imported for the annotations only: importing the unit module for real
    # would run into the import of this module in ``UnitWordRelation.save()``.
    from .models.unit import Unit, UnitWordRelation

logger = logging.getLogger(__name__)


def experts_of_units(units: Iterable[Unit]) -> dict[User, set[int]]:
    """
    Find the experts of the given units.

    Args:
        units: The units whose experts are wanted

    Returns:
        dict: Every expert mapped to the ids of the given units they review
    """
    experts: dict[User, set[int]] = defaultdict(set)
    for review in Review.objects.filter(unit_word__unit__in=units).select_related(
        "reviewer", "unit_word"
    ):
        experts[review.reviewer].add(review.unit_word.unit_id)
    return experts


def notify_units_assigned(
    expert: User,
    units: Iterable[Unit],
    assigned_by: AbstractBaseUser | AnonymousUser | None = None,
) -> None:
    """
    Tell an expert that units were assigned to them for review.

    Args:
        expert: The user the units were assigned to
        units: The newly assigned units
        assigned_by: The user who assigned them, never notified about it
    """
    if not expert.email or _is_same_user(expert, assigned_by):
        return
    PendingNotification.objects.bulk_create(
        PendingNotification(
            expert=expert,
            notification_type=NotificationType.UNIT_ASSIGNED,
            unit=unit,
        )
        for unit in dict.fromkeys(units)
    )


def notify_words_added(
    relations: Iterable[UnitWordRelation],
    added_by: AbstractBaseUser | AnonymousUser | None = None,
) -> None:
    """
    Tell the experts of units that words were added to them.

    Args:
        relations: The newly created unit-word relations
        added_by: The user who added the words, never notified about it
    """
    relations = list(relations)
    if not relations:
        return
    experts = experts_of_units({relation.unit for relation in relations})
    PendingNotification.objects.bulk_create(
        PendingNotification(
            expert=expert,
            notification_type=NotificationType.WORD_ADDED,
            unit_word=relation,
        )
        for expert, unit_ids in experts.items()
        if expert.email and not _is_same_user(expert, added_by)
        for relation in relations
        if relation.unit_id in unit_ids
    )


def notify_image_added(
    relation: UnitWordRelation,
    added_by: AbstractBaseUser | AnonymousUser | None = None,
) -> None:
    """
    Tell the experts of a unit that a word of it got a new image.

    Args:
        relation: The unit-word relation whose image was uploaded or generated
        added_by: The user who added the image, never notified about it
    """
    PendingNotification.objects.bulk_create(
        PendingNotification(
            expert=expert,
            notification_type=NotificationType.IMAGE_ADDED,
            unit_word=relation,
        )
        for expert in experts_of_units([relation.unit])
        if expert.email and not _is_same_user(expert, added_by)
    )


def send_digests() -> int:
    """
    Send every expert with pending notifications one email listing all of
    them, and delete them afterwards.

    Notifications about content the expert no longer reviews are dropped.
    Notifications of an expert whose email could not be sent are kept for the
    next run.

    Returns:
        int: The number of emails sent
    """
    sent = 0
    expert_ids = (
        PendingNotification.objects.values_list("expert_id", flat=True)
        .distinct()
        .order_by("expert_id")
    )
    for expert in get_user_model().objects.filter(pk__in=list(expert_ids)):
        notifications = list(
            expert.pending_notifications.select_related(
                "unit", "unit_word__unit", "unit_word__word"
            ).order_by("created_at", "pk")
        )
        try:
            sent += _send_digest(expert, notifications)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Sending the digest to %r failed", expert.username)
            continue
        PendingNotification.objects.filter(
            pk__in=[notification.pk for notification in notifications]
        ).delete()
    return sent


def _send_digest(expert: User, notifications: list[PendingNotification]) -> bool:
    """
    Send an expert the digest of their notifications.

    Args:
        expert: The recipient
        notifications: The pending notifications of the expert

    Returns:
        bool: Whether an email was sent

    Raises:
        Exception: If the email could not be sent
    """
    reviewed_unit_ids = set(
        Review.objects.filter(reviewer=expert).values_list(
            "unit_word__unit_id", flat=True
        )
    )
    items: dict[str, dict[str, None]] = {
        notification_type: {} for notification_type in NotificationType
    }
    for notification in notifications:
        unit_id: int | None
        if notification.unit_word:
            unit_id, label = notification.unit_word.unit_id, str(notification.unit_word)
        else:
            unit_id, label = notification.unit_id, str(notification.unit)
        if unit_id in reviewed_unit_ids:
            items[notification.notification_type][label] = None
    # A new word is reviewed with its image, so its image is no news of its own
    for label in items[NotificationType.WORD_ADDED]:
        items[NotificationType.IMAGE_ADDED].pop(label, None)

    sections = [
        (intro, list(items[notification_type]))
        for notification_type, intro in (
            (
                NotificationType.UNIT_ASSIGNED,
                _("The following units were assigned to you for review:"),
            ),
            (
                NotificationType.WORD_ADDED,
                _("The following words were added to units you review:"),
            ),
            (
                NotificationType.IMAGE_ADDED,
                _("New images were added to the following words of units you review:"),
            ),
        )
        if items[notification_type]
    ]
    if not expert.email or not sections:
        return False
    message = render_to_string(
        "cmsv2/emails/expert_notification.txt",
        {
            "expert": expert,
            "sections": sections,
            "review_url": settings.BASE_URL + reverse("expert_access:review"),
        },
    )
    send_mail(_("New content to review"), message, None, [expert.email])
    return True


def _is_same_user(expert: User, user: AbstractBaseUser | AnonymousUser | None) -> bool:
    return user is not None and user.pk == expert.pk
