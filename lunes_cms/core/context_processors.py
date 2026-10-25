"""
Context processors pass additional variables to templates (see :ref:`context-processors`).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest

from ..cms.feedback_filter import filter_feedback_by_creator
from ..cms.models import Feedback
from ..cmsv2.feedback_filter import (
    filter_feedback_by_creator_and_area as filter_feedbackv2_by_creator_and_area,
)
from ..cmsv2.models import Feedback as FeedbackV2
from ..cmsv2.models import Notification


def legal_links_processor(  # pylint: disable=unused-argument
    request: HttpRequest,
) -> dict[str, Any]:
    """
    This context processor injects the URLs of the privacy policy and the imprint into the
    template context. They are read per request instead of being passed as static template
    context, so that the login page (which is rendered for anonymous users) gets them, too.

    :param request: The current http request
    :type request: ~django.http.HttpRequest

    :return: The template context containing the legal link URLs
    :rtype: dict
    """
    return {
        "privacy_policy_url": settings.PRIVACY_POLICY_URL,
        "imprint_url": settings.IMPRINT_URL,
    }


def feedback_processor(request: HttpRequest) -> dict[str, Any]:
    """
    This context processor injects the number of unread feedback entries into the template context.

    :param request: The current http request
    :type request: ~django.http.HttpRequest

    :return: The template context containing the number of unread feedback entries
    :rtype: dict
    """
    unread_feedback_entries = Feedback.objects.filter(read_by=None)

    if not request.user.is_superuser:
        unread_feedback_entries = filter_feedback_by_creator(
            unread_feedback_entries, request.user
        )

    return {"unread_feedback_count": unread_feedback_entries.count()}


def feedbackv2_processor(request: HttpRequest) -> dict[str, Any]:
    """
    This context processor injects the number of unread feedback (cms v2) entries into the template context.

    :param request: The current http request
    :type request: ~django.http.HttpRequest

    :return: The template context containing the number of unread feedback entries
    :rtype: dict
    """
    unread_feedback_entries = FeedbackV2.objects.filter(read_by=None)

    if not request.user.is_superuser:
        unread_feedback_entries = filter_feedbackv2_by_creator_and_area(
            unread_feedback_entries, request.user  # type: ignore[arg-type]
        )

    return {"unread_feedbackv2_count": unread_feedback_entries.count()}


def notification_processor(request: HttpRequest) -> dict[str, Any]:
    """
    This context processor injects the number of unread notifications of the current user
    into the template context.

    :param request: The current http request
    :type request: ~django.http.HttpRequest

    :return: The template context containing the number of unread notifications
    :rtype: dict
    """
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}
    return {
        "unread_notification_count": Notification.objects.filter(
            recipient=request.user, read_at=None
        ).count()
    }
