"""
E2E test: Einheit hinzufügen — generates user_docs/add_unit.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

from conftest import ASSETS_DIR

JOB_NAME = "Eisverkäufer/-in"
UNIT_NAME = "Grundlagen und Methoden"


@pytest.mark.e2e
def test_add_unit(
    page: Page,
    document,
    base_url: str,
    login,
    add_job: Callable,
    add_unit: Callable,
    delete_unit: Callable,
    delete_job: Callable,
) -> None:
    add_job(JOB_NAME)

    with document.step(
        "Einheiten-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Einheit**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/unit/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/")

    with document.step(
        "Neue Einheit anlegen",
        description='Klicken Sie oben rechts auf den Button **„Einheit hinzufügen"**.',
    ):
        page.click("a[href='/de/admin/cmsv2/unit/add/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/add/")

    page.fill("[name=title]", UNIT_NAME)
    with document.step(
        "Titel eingeben",
        description=f'Geben Sie den Titel der Einheit in das Feld **„Einheit"** ein, z. B. `{UNIT_NAME}`.',
    ):
        pass

    page.fill("[name=description]", f"Vokabeln zu {UNIT_NAME}")
    with document.step(
        "Beschreibung eingeben",
        description='Geben Sie eine Beschreibung in das Feld **„Beschreibung"** ein.',
    ):
        pass

    page.set_input_files("[name=icon]", str(ASSETS_DIR / "tester.png"))
    with document.step(
        "Icon hochladen",
        description='Klicken Sie auf **„Durchsuchen"** neben dem Feld **„Icon"** und wählen Sie eine Bilddatei aus.',
    ):
        pass

    page.select_option("#id_jobs", label=JOB_NAME)
    with document.step(
        "Beruf auswählen",
        description=f'Wählen Sie im Feld **„Beruf"** den Job aus zu dem die Einheit gehört z.B. **„{JOB_NAME}"**.',
    ):
        pass

    with document.step(
        "Einheit speichern",
        description='Klicken Sie auf **„Sichern"**, um die neue Einheit zu speichern.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Einheit wurde gespeichert",
        description=f'Die neue Einheit **„{UNIT_NAME}"** erscheint nun in der Einheiten-Übersicht.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(UNIT_NAME)
        page.locator(
            "th.field-title a", has_text=UNIT_NAME
        ).scroll_into_view_if_needed()
        expect(page.locator("th.field-title a", has_text=UNIT_NAME)).to_be_visible()

    delete_unit(UNIT_NAME)
    delete_job(JOB_NAME)
