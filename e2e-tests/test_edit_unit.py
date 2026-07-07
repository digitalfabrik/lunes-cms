"""
E2E test: Einheit bearbeiten — generates user_docs/edit_unit.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME_1 = "Informatiker/-in"
JOB_NAME_2 = "Einzelhandelskaufmann/-frau"
UNIT_NAME = "Werkzeuge und Materialien"
UNIT_NAME_UPDATED = "Werkzeuge und Materialien II"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
UNIT_DESCRIPTION_UPDATED = f"Vokabeln zu {UNIT_NAME_UPDATED}"


@pytest.mark.e2e
def test_edit_unit(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_job: Callable,
    add_unit: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    request: pytest.FixtureRequest,
) -> None:
    def _delete_unit() -> None:
        try:
            delete_unit(UNIT_NAME_UPDATED)
        except Exception:
            delete_unit(UNIT_NAME)

    request.addfinalizer(lambda: delete_job(JOB_NAME_2))
    request.addfinalizer(lambda: delete_job(JOB_NAME_1))
    request.addfinalizer(_delete_unit)
    add_job(JOB_NAME_1)
    add_job(JOB_NAME_2)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME_1)

    with document.step(
        "Einheit-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Einheit**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/unit/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/")

    unit_link = page.locator("th.field-title a", has_text=UNIT_NAME)
    unit_link.scroll_into_view_if_needed()
    unit_link.click()

    with document.step(
        "Zur Einheit navigieren und öffnen",
        description=f'Scrollen Sie in der Übersicht zu einer Einheit z.B. **„{UNIT_NAME}"** und klicken Sie darauf.',
    ):
        pass

    page.fill("[name=title]", UNIT_NAME_UPDATED)
    page.fill("[name=description]", UNIT_DESCRIPTION_UPDATED)
    page.select_option("#id_jobs", label=JOB_NAME_2)

    with document.step(
        "Felder anpassen",
        description="Passen Sie die entsprechenden Felder an.",
    ):
        pass

    with document.step(
        "Änderungen speichern",
        description='Klicken Sie auf **„Sichern"**, um die Änderungen zu speichern.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Einheit wurde aktualisiert",
        description=f'Die Einheit **„{UNIT_NAME_UPDATED}"** wurde erfolgreich gespeichert.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(UNIT_NAME_UPDATED)
