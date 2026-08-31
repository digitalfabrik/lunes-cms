from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def review(request: HttpRequest) -> HttpResponse:
    """The expert review view

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    return render(request, "review_view.html", {})
