"""
Context processors pass additional variables to templates (see :ref:`context-processors`).
"""
from ..cms.models import Feedback


# pylint: disable=unused-variable
def feedback_processor(request):
    """
    This context processor injects the number of unread feedback entries into the template context.

    :param request: The current http request
    :type request: ~django.http.HttpRequest

    :return: The template context containing the number of unread feedback entries
    :rtype: dict
    """
    return {"unread_feedback_cnt": Feedback.objects.filter(read_by=None).count()}
