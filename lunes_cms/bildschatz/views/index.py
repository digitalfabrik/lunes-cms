from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def index(request: HttpRequest) -> HttpResponse:
    """
    Render the public Bildschatz single-page website.

    The actual search is performed client-side against the public
    ``/api/v2/words/`` endpoint. The search term is read from the ``q`` query
    parameter so that result pages are shareable via their URL.

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    return render(request, "bildschatz.html")
