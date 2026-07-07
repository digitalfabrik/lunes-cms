"""
E2E test: Gruppe löschen — generates user_docs/delete_group.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

GROUP_NAME = "Neue Vokabelverwalter:innen"


@pytest.mark.e2e
def test_delete_group(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_group: Callable,
    delete_group: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_group(GROUP_NAME))
    add_group(GROUP_NAME)

    with document.step(
        "Gruppen-Bereich öffnen",
        description='Klicken Sie im linken Navigationsmenü im Bereich **„Authentifizierung und Autorisierung"** auf **„Gruppen"**.',
    ):
        page.goto(f"{base_url}/de/admin/auth/group/")
        expect(page).to_have_url(f"{base_url}/de/admin/auth/group/")

    with document.step(
        "Gruppe auswählen",
        description=f'Klicken Sie auf die Gruppe **„{GROUP_NAME}"**, um sie zu öffnen.',
    ):
        page.get_by_role("link", name=GROUP_NAME).first.click()

    with document.step(
        "Gruppe löschen",
        description='Klicken Sie unten links auf **„Löschen"**.',
    ):
        page.get_by_role("link", name="Löschen").click()

    with document.step(
        "Löschen bestätigen",
        description='Bestätigen Sie das Löschen mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        page.locator("input[type=submit]").click()
        expect(page.locator(".alert-success")).to_be_visible()
