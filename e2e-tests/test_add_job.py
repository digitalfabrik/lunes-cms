"""
E2E test: Job hinzufügen — generates user_docs/add_job.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

from conftest import ASSETS_DIR

JOB_NAME = "Tester/-in"


@pytest.mark.e2e
@pytest.mark.xdist_group("vocabulary_management")
def test_add_job(
    page: Page, document, base_url: str, login, delete_job: Callable
) -> None:
    with document.step(
        "Berufe-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Berufe**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/job/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/")

    with document.step(
        "Neuen Beruf anlegen",
        description='Klicken Sie oben rechts auf den Button **„Beruf hinzufügen"**.',
    ):
        page.click("a[href='/de/admin/cmsv2/job/add/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/add/")

    page.fill("[name=name]", JOB_NAME)
    with document.step(
        "Beruf-Name eingeben",
        description=f'Geben Sie den Namen des Berufs in das Feld **„Beruf"** ein, z. B. `{JOB_NAME}`.',
    ):
        pass

    page.set_input_files("[name=icon]", str(ASSETS_DIR / "tester.png"))
    with document.step(
        "Icon hochladen",
        description='Klicken Sie auf **„Durchsuchen"** neben dem Feld **„Icon"** und wählen Sie eine Bilddatei (PNG, JPG) aus.',
    ):
        pass

    with document.step(
        "Beruf speichern",
        description='Klicken Sie auf **„Sichern"**, um den neuen Beruf zu speichern.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Beruf wurde gespeichert",
        description="Der neue Beruf erscheint nun in der Berufs-Übersicht. Eine grüne Erfolgsmeldung bestätigt die Speicherung.",
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(JOB_NAME)
        page.locator("th.field-name a", has_text=JOB_NAME).scroll_into_view_if_needed()

    delete_job(JOB_NAME)
