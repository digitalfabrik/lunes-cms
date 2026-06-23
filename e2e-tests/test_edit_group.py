"""
E2E test: Gruppe bearbeiten — generates user_docs/edit_group.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

GROUP_NAME = "Neue Vokabelverwalter:innen"


@pytest.mark.e2e
def test_edit_group(
    page: Page,
    document,
    base_url: str,
    login,
    add_group: Callable,
    delete_group: Callable,
) -> None:
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

    page.locator("#id_permissions_selected_input").press_sequentially("Vokabeln")
    page.wait_for_timeout(200)
    page.locator("#id_permissions_remove_all").scroll_into_view_if_needed()

    with document.step(
        "Berechtigungen filtern und entfernen",
        description='Nutzen Sie das Suchfeld über den ausgewählten Berechtigungen, um nach einer Kategorie zu filtern. Klicken Sie dann auf **„Remove all Berechtigungen"**, um alle gefilterten Einträge zu entfernen.',
    ):
        page.locator("#id_permissions_remove_all").click()
        page.locator("#id_permissions_selected_input").select_text()
        page.locator("#id_permissions_selected_input").press("Backspace")

    page.evaluate("window.scrollTo(0, 0)")

    with document.step(
        "Änderungen speichern",
        description='Klicken Sie auf **„Sichern"**, um die Änderungen zu speichern.',
    ):
        page.get_by_role("button", name="Sichern", exact=True).click()
        expect(page.locator(".alert-success")).to_be_visible()

    delete_group(GROUP_NAME)
