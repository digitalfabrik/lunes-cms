"""
E2E test: Gruppe anlegen — generates user_docs/add_group.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage, PERMISSION_GROUPS
from playwright.sync_api import expect, Page

GROUP_NAME = "Neue Vokabelverwalter:innen"


@pytest.mark.e2e
def test_add_group(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    delete_group: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_group(GROUP_NAME))
    with document.step(
        "Gruppen-Bereich öffnen",
        description='Klicken Sie im linken Navigationsmenü im Bereich **„Authentifizierung und Autorisierung"** auf **„Gruppen"**.',
    ):
        page.get_by_role("link", name="Gruppen", exact=True).click()
        expect(page).to_have_url(f"{base_url}/de/admin/auth/group/")

    with document.step(
        "Neue Gruppe anlegen",
        description='Klicken Sie oben rechts auf **„Gruppe hinzufügen"**.',
    ):
        page.get_by_role("link", name="Gruppe hinzufügen").click()
        expect(page).to_have_url(f"{base_url}/de/admin/auth/group/add/")

    with document.step(
        "Gruppenname eingeben",
        description=f'Geben Sie im Feld **„Name"** den Gruppennamen **„{GROUP_NAME}"** ein.',
    ):
        page.fill("[name=name]", GROUP_NAME)

    with document.step(
        "Berechtigungen filtern und auswählen",
        description="Nutzen Sie das Suchfeld über der Berechtigungsliste, um nach Kategorien zu filtern. Wählen Sie die gefilterten Einträge aus und klicken Sie auf den Hinzufügen-Button.",
    ):
        filter_input = page.locator("#id_permissions_input")
        choose_all = page.locator("#id_permissions_add_all")
        for search_term, _ in PERMISSION_GROUPS:
            filter_input.press_sequentially(search_term)
            page.wait_for_timeout(200)
            choose_all.click()
            filter_input.select_text()
            filter_input.press("Backspace")
            page.wait_for_timeout(200)
        page.locator("#id_permissions_to").scroll_into_view_if_needed()

    with document.step(
        "Gruppe speichern",
        description='Klicken Sie auf **„Sichern"**, um die neue Gruppe anzulegen.',
    ):
        page.evaluate("window.scrollTo(0, 0)")
        page.get_by_role("button", name="Sichern", exact=True).click()
        expect(page.locator(".alert-success")).to_be_visible()
