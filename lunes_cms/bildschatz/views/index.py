from __future__ import annotations

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from ..access import may_use_bildschatz


def index(request: HttpRequest) -> HttpResponse:
    """
    Render the public Bildschatz single-page website.

    The actual search is performed client-side against the public
    ``/api/v2/words/`` endpoint. The search term is read from the ``q`` query
    parameter so that result pages are shareable via their URL.

    Until Bildschatz is released to the public, visitors who are not logged in
    to the CMS are sent to the login first (see :func:`~lunes_cms.bildschatz.access.may_use_bildschatz`).

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    if not may_use_bildschatz(request.user):
        return redirect_to_login(request.get_full_path())
    return render(request, "bildschatz.html")
