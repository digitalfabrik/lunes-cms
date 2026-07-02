"""
E2E test: Benutzer:in bearbeiten (Berechtigungen) — generates user_docs/edit_user_permissions.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

USERNAME = "test_lunes_user_edit_permissions"
PASSWORD = "lunes2024!"


@pytest.mark.e2e
def test_edit_user_permissions(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_user: Callable,
    delete_user: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_user(USERNAME))
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

    page.locator("#id_groups_from").select_option(label="Vokabelverwalter:innen")
    page.locator("#id_groups_add").click()
    page.locator("#id_groups_to").scroll_into_view_if_needed()

    with document.step(
        "Gruppe zuweisen",
        description='Scrollen Sie zum Bereich **„Berechtigungen"**, wählen Sie **„Vokabelverwalter:innen"** aus den verfügbaren Gruppen aus und klicken Sie auf den Hinzufügen-Button. Die Gruppe erscheint nun unter **„Ausgewählte Gruppen"**.',
    ):
        pass

    page.evaluate("window.scrollTo(0, 0)")

    with document.step(
        "Änderungen speichern",
        description='Scrollen Sie wieder nach oben und klicken Sie auf **„Sichern"**.',
    ):
        page.get_by_role("button", name="Sichern", exact=True).click()
        expect(page.locator(".alert-success")).to_be_visible()
