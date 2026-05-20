"""
E2E test: Benutzer:in anlegen — generates user_docs/add_user.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

USERNAME = "test_lunes_user"
PASSWORD = "lunes2024!"


@pytest.mark.e2e
@pytest.mark.xdist_group("auth_management")
def test_add_user(
    page: Page,
    document,
    base_url: str,
    login,
    delete_user: Callable,
) -> None:
    with document.step(
        "Benutzer-Bereich öffnen",
        description='Klicken Sie im linken Navigationsmenü im Bereich **„Authentifizierung und Autorisierung"** auf **„Benutzer"**.',
    ):
        page.get_by_role("link", name="Benutzer", exact=True).click()
        expect(page).to_have_url(f"{base_url}/de/admin/auth/user/")

    with document.step(
        "Neuen Benutzer anlegen",
        description='Klicken Sie oben rechts auf **„Benutzer hinzufügen"**.',
    ):
        page.get_by_role("link", name="Benutzer hinzufügen").click()
        expect(page).to_have_url(f"{base_url}/de/admin/auth/user/add/")

    with document.step(
        "Benutzerdaten eingeben",
        description=f'Geben Sie einen **Benutzernamen** ein. Das **Passwort** muss mindestens 8 Zeichen enthalten und darf nicht komplett aus Ziffern bestehen. Wiederholen Sie das Passwort im Feld **„Passwort bestätigen"**.',
    ):
        page.fill("[name=username]", USERNAME)
        page.fill("[name=password1]", PASSWORD)
        page.fill("[name=password2]", PASSWORD)

    with document.step(
        "Benutzer speichern",
        description='Klicken Sie auf **„Speichern"**, um den neuen Benutzer anzulegen.',
    ):
        page.click("[name=_save]")
        expect(page.locator(".alert-success")).to_be_visible()

    delete_user(USERNAME)
