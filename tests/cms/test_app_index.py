"""
Tests for the admin's app-index breadcrumb links (issue #896).

``lunes_cms.cms.admin`` monkey-patches ``AdminSite.get_app_list`` to apply a
custom app/model ordering. Its signature didn't accept the ``app_label``
argument Django's ``AdminSite.app_index`` view passes when rendering a
single app's own index page (e.g. by following the "Vokabelverwaltung v2"
breadcrumb link) — crashing with a ``TypeError`` that surfaced to users as a
500 Server Error.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.parametrize("app_label", ["cmsv2", "cms", "auth"])
@pytest.mark.django_db()
def test_app_index_page_does_not_error(admin_client: Client, app_label: str) -> None:
    """Following an app's breadcrumb link (its app-index page) must render,
    not crash — this is exactly what a user does when clicking the parent
    category in the breadcrumb trail."""
    response = admin_client.get(reverse("admin:app_list", args=[app_label]))

    assert response.status_code == 200
