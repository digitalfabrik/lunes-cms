"""
Email notifications for experts, see #650.

An expert of a unit is a user who has been assigned words of that unit for
review (see :class:`~lunes_cms.cmsv2.models.review.Review`). Experts are told by
email when there is new content for them to review:

* units were assigned to them,
* words were added to a unit they review,
* an image was uploaded or generated for a word of a unit they review.

Every notification is sent once the surrounding transaction is committed, so
nothing is announced that is rolled back afterwards, and a failing mail server
never breaks the change that triggered the notification.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable, TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

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
        assigned_by: The user who assigned them, who is not notified about
            their own action
    """
    units = list(dict.fromkeys(units))
    if not units or _is_same_user(expert, assigned_by):
        return
    _send(
        expert,
        _("New units to review"),
        _("The following units were assigned to you for review:"),
        [str(unit) for unit in units],
    )


def notify_words_added(
    relations: Iterable[UnitWordRelation],
    added_by: AbstractBaseUser | AnonymousUser | None = None,
) -> None:
    """
    Tell the experts of units that words were added to them.

    Args:
        relations: The newly created unit-word relations
        added_by: The user who added the words, who is not notified about
            their own action
    """
    relations = list(relations)
    if not relations:
        return
    experts = experts_of_units({relation.unit for relation in relations})
    for expert, unit_ids in experts.items():
        if _is_same_user(expert, added_by):
            continue
        items = [
            str(relation) for relation in relations if relation.unit_id in unit_ids
        ]
        _send(
            expert,
            _("New words to review"),
            _("The following words were added to units you review:"),
            items,
        )


def notify_image_added(
    relation: UnitWordRelation,
    added_by: AbstractBaseUser | AnonymousUser | None = None,
) -> None:
    """
    Tell the experts of a unit that a word of it got a new image.

    Args:
        relation: The unit-word relation whose image was uploaded or generated
        added_by: The user who added the image, who is not notified about
            their own action
    """
    for expert in experts_of_units([relation.unit]):
        if _is_same_user(expert, added_by):
            continue
        _send(
            expert,
            _("New image to review"),
            _("A new image was added to a word of a unit you review:"),
            [str(relation)],
        )


def _is_same_user(expert: User, user: AbstractBaseUser | AnonymousUser | None) -> bool:
    return user is not None and user.pk == expert.pk


def _send(expert: User, subject: str, intro: str, items: list[str]) -> None:
    """
    Send a notification to an expert once the current transaction is committed.

    Args:
        expert: The recipient
        subject: The subject of the email
        intro: The sentence introducing the new content
        items: The labels of the new content
    """
    if not expert.email or not items:
        return
    message = render_to_string(
        "cmsv2/emails/expert_notification.txt",
        {
            "expert": expert,
            "intro": intro,
            "items": items,
            "review_url": settings.BASE_URL + reverse("expert_access:review"),
        },
    )

    def send() -> None:
        try:
            send_mail(subject, message, None, [expert.email])
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Sending a notification to %r failed", expert.username)

    transaction.on_commit(send)
