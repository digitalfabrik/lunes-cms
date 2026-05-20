"""
E2E test: Benutzer:in löschen — generates user_docs/delete_user.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

USERNAME = "test_lunes_user_neu"
PASSWORD = "lunes2024!"


@pytest.mark.e2e
@pytest.mark.xdist_group("auth_management")
def test_delete_user(
    page: Page,
    document,
    base_url: str,
    login,
    add_user: Callable,
) -> None:
    add_user(USERNAME, PASSWORD)

    page.get_by_role("link", name="Benutzer", exact=True).click()
    expect(page).to_have_url(f"{base_url}/de/admin/auth/user/")

    with document.step(
        "Benutzer-Bereich öffnen",
        description='Klicken Sie im linken Navigationsmenü im Bereich **„Authentifizierung und Autorisierung"** auf **„Benutzer"**, um die Übersicht aller Benutzer:innen zu öffnen.',
    ):
        page.fill("#searchbar", USERNAME)
        page.get_by_role("button", name="Suchen").click()

    page.get_by_role("link", name=USERNAME).first.click()

    with document.step(
        "Benutzer:in löschen",
        description=f'Wählen Sie die Benutzer:in **„{USERNAME}"** aus und klicken Sie rechts oben auf **„Löschen"**.',
    ):
        page.get_by_role("link", name="Löschen").click()

    with document.step(
        "Löschung bestätigen",
        description='In der Zusammenfassung wird **„Benutzer: 1"** angezeigt. Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        expect(page.locator("tr", has_text="Benutzer")).to_contain_text("1")
        page.locator("input[type=submit]").click()
        expect(page.locator(".alert-success")).to_contain_text(USERNAME)
