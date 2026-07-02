"""
E2E test: Mehrere Einheiten löschen — generates user_docs/bulk_delete_units.md
"""

from __future__ import annotations

from functools import partial
from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME = "Maler/-in"
UNIT_NAMES = [
    "Farben und Lacke",
    "Pinsel und Werkzeuge",
    "Sicherheit auf der Baustelle",
]


@pytest.mark.e2e
def test_bulk_delete_units(
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
    request.addfinalizer(lambda: delete_job(JOB_NAME))
    for unit_name in UNIT_NAMES:
        request.addfinalizer(partial(delete_unit, unit_name))
    add_job(JOB_NAME)
    for unit_name in UNIT_NAMES:
        add_unit(unit_name, f"Vokabeln zu {unit_name}", JOB_NAME)

    with document.step(
        "Einheit-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Einheit**.",
    ):
        page.goto(f"{base_url}/de/admin/cmsv2/unit/?all=")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/?all=")

    for unit_name in UNIT_NAMES:
        page.locator(
            "tr", has=page.locator("th.field-title a", has_text=unit_name)
        ).locator("input[type=checkbox]").check()
    page.locator(
        "th.field-title a", has_text=UNIT_NAMES[0]
    ).scroll_into_view_if_needed()
    with document.step(
        "Einheiten auswählen",
        description='Aktivieren Sie die Checkboxen neben den Einheiten **„Farben und Lacke"**, **„Pinsel und Werkzeuge"** und **„Sicherheit auf der Baustelle"**.',
    ):
        pass

    page.locator("button[name=index][value='0']").scroll_into_view_if_needed()
    page.evaluate("""
        const select = document.querySelector('select[name=action]');
        select.value = 'delete_selected';
        $(select).trigger('change');
    """)
    with document.step(
        'Aktion "Ausgewählte Einheit löschen" auswählen und ausführen',
        description='Wählen Sie im Aktions-Dropdown **"Ausgewählte Einheit löschen"** aus und klicken Sie auf **„Go"**.',
    ):
        page.click("button[name=index][value='0']")

    with document.step(
        "Löschung bestätigen",
        description='Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        expect(
            page.locator("tr", has=page.get_by_text("Einheit", exact=True))
            .locator("td")
            .nth(1)
        ).to_have_text(str(len(UNIT_NAMES)))
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/?all=")

    with document.step(
        "Erfolg — Einheiten wurden gelöscht",
        description="Alle drei Einheiten sind nicht mehr in der Übersicht vorhanden.",
    ):
        for unit_name in UNIT_NAMES:
            expect(page.locator("th.field-title a", has_text=unit_name)).to_have_count(
                0
            )
