"""
Context processors pass additional variables to templates (see :ref:`context-processors`).
"""
from ..cms.models import Feedback
from ..cms.feedback_filter import filter_feedback_by_creator


def feedback_processor(request):
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
