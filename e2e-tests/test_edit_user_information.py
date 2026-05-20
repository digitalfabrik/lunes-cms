"""
E2E test: Benutzer:in bearbeiten (Informationen) — generates user_docs/edit_user_information.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

USERNAME = "test_lunes_user_edit_info"
PASSWORD = "lunes2024!"


@pytest.mark.e2e
@pytest.mark.xdist_group("auth_management")
def test_edit_user_information(
    page: Page,
    document,
    base_url: str,
    login,
    add_user: Callable,
    delete_user: Callable,
) -> None:
    add_user(USERNAME, PASSWORD)

    page.goto(f"{base_url}/de/admin/auth/user/")

    with document.step(
        "Benutzer-Bereich öffnen",
        description='Wählen Sie im Navigationsmenü **„Benutzer"**, um die Übersicht aller Benutzer:innen zu öffnen.',
    ):
        page.get_by_role("link", name=USERNAME).first.click()

    with document.step(
        "Benutzer:in auswählen",
        description=f'Wählen Sie die Benutzer:in **„{USERNAME}"** aus der Liste aus.',
    ):
        pass

    page.fill("[name=first_name]", "Erika")
    page.fill("[name=last_name]", "Muster")
    page.fill("[name=email]", "erika.muster@example.com")
    page.locator("[name=email]").scroll_into_view_if_needed()

    with document.step(
        "Persönliche Informationen eingeben",
        description='Scrollen Sie zum Bereich **„Persönliche Informationen"** und füllen Sie die Felder **„Vorname"**, **„Nachname"** und **„E-Mail-Adresse"** aus.',
    ):
        pass

    page.evaluate("window.scrollTo(0, 0)")

    with document.step(
        "Änderungen speichern",
        description='Scrollen Sie wieder nach oben und klicken Sie auf **„Sichern"**.',
    ):
        page.get_by_role("button", name="Sichern", exact=True).click()
        expect(page.locator(".alert-success")).to_be_visible()

    delete_user(USERNAME)
