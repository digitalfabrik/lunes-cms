from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.query import Prefetch
from django.utils.translation import gettext_lazy as _

from lunes_cms.cmsv2.models import Review, Unit, UnitWordRelation, Word
from lunes_cms.cmsv2.notifications import notify_units_assigned

if TYPE_CHECKING:
    # `_StrOrPromise` only exists in django-stubs, not at runtime.
    from django.utils.functional import _StrOrPromise
    from django_stubs_ext import WithAnnotations


class ReviewRelations(TypedDict):
    """
    The relations prefetched by :func:`available_units_per_word`.
    """

    available_review_relations: list[UnitWordRelation]


def available_units_per_word(
    words: QuerySet[Word], *, limit_units_to: QuerySet[Unit]
) -> tuple[
    list[WithAnnotations[Word, ReviewRelations]],
    list[WithAnnotations[Word, ReviewRelations]],
]:
    """
    Returns words prefetched with their units and words without units.
    The available unit word relations are prefetched to `available_review_relations`.

    :param words: The words to assign for review
    :param limit_units_to: The available units that can be used for each word
    :return: a tuple of lists, (words_with_unit, words_without_unit)
    """
    prefetched_words = list(
        words.prefetch_related(
            Prefetch(
                "unit_word_relations",
                queryset=UnitWordRelation.objects.filter(
                    unit__in=limit_units_to
                ).select_related("unit"),
                to_attr="available_review_relations",
            ),
        ).order_by("-word")
    )
    words_without_unit = [
        word for word in prefetched_words if len(word.available_review_relations) == 0
    ]
    words_with_unit = [
        word for word in prefetched_words if len(word.available_review_relations) > 0
    ]

    return words_with_unit, words_without_unit


def assign_reviews(
    unit_words: QuerySet[UnitWordRelation],
    *,
    reviewer: User,
    assigner: AbstractBaseUser | AnonymousUser,
) -> _StrOrPromise:
    """
    Assigns reviews to the assigned units.
    """
    unit_word_list = list(unit_words)

    with transaction.atomic():
        User.objects.select_for_update().get(pk=reviewer.pk)
        already_assigned = set(
            reviewer.review_assignments.filter(
                unit_word__in=unit_word_list
            ).values_list("unit_word_id", flat=True)
        )
        created = Review.objects.bulk_create(
            Review(unit_word=unit_word, reviewer=reviewer, assigned_by_id=assigner.pk)
            for unit_word in unit_word_list
            if unit_word.pk not in already_assigned
        )

    notify_units_assigned(
        reviewer,
        (review.unit_word.unit for review in created),
        assigned_by=assigner,
    )

    return _("Assigned %(new)d word(s) to %(user)s (%(skipped)d already assigned).") % {
        "new": len(created),
        "skipped": len(already_assigned),
        "user": reviewer,
    }
