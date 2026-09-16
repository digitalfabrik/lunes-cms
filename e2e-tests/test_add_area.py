"""
E2E test: Bereich hinzufügen — generates user_docs/add_area.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

AREA_NAME = "Testbereich"
INVALID_CODE = "kurs"
VALID_CODE = "TESTKURS2026"


@pytest.fixture
def delete_area(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes an area by name from the CMS admin."""

    def _delete(area_name: str) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/area/")
        locator = page.locator("th.field-name a", has_text=area_name)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.mark.e2e
def test_add_area(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    delete_area: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_area(AREA_NAME))

    with document.step(
        "Bereiche öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Bereiche**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/area/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/area/")

    with document.step(
        "Neuen Bereich anlegen",
        description='Klicken Sie oben rechts auf den Button **„Bereich hinzufügen"**.',
    ):
        page.click("a[href='/de/admin/cmsv2/area/add/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/area/add/")

    page.fill("[name=name]", AREA_NAME)
    with document.step(
        "Name des Bereichs eingeben",
        description=(
            'Geben Sie den Namen des Bereichs in das Feld **„Bereich"** ein, '
            f"z. B. `{AREA_NAME}`. Der Name ist eindeutig: zwei Bereiche "
            "können nicht gleich heißen."
        ),
    ):
        pass

    with document.step(
        "Administrator:innen auswählen",
        description=(
            'Wählen Sie unter **„Administratoren"** die Benutzer:innen aus, '
            "die diesen Bereich verwalten sollen, und verschieben Sie sie mit "
            "dem Pfeil nach rechts. Diese Benutzer:innen sehen anschließend "
            "nur noch die Berufe, Einheiten und Vokabeln ihres Bereichs."
        ),
    ):
        page.locator("#id_admins_add_all").scroll_into_view_if_needed()

    with document.step(
        "Ungültigen Code korrigieren",
        description=(
            "Jeder Bereich kann beliebig viele **Codes** haben, mit denen später "
            "der Zugang zu den Inhalten des Bereichs freigeschaltet wird. Ein "
            "Code besteht aus mindestens 8 Zeichen und darf nur Ziffern und "
            "Großbuchstaben enthalten — andernfalls meldet das Formular einen "
            "Fehler. Ein Vorschlag ist bereits eingetragen, Sie können ihn aber "
            "auch überschreiben."
        ),
    ):
        code_input = page.locator("[name=codes-0-code]")
        code_input.scroll_into_view_if_needed()
        code_input.fill(INVALID_CODE)
        page.click("[name=_continue]")
        expect(page.locator(".errorlist")).to_be_visible()
        # The next screenshot is taken at the top of the following block, so
        # bring the rejected code into view for it.
        page.locator("[name=codes-0-code]").scroll_into_view_if_needed()

    with document.step(
        "Gültigen Code eintragen und speichern",
        description=(
            f"Tragen Sie einen gültigen Code ein, z. B. `{VALID_CODE}`, und "
            'klicken Sie auf **„Sichern"**. Über **„Add another Code"** können '
            "Sie weitere Codes für denselben Bereich anlegen, etwa einen pro "
            "Kurs oder Kooperation."
        ),
    ):
        code_input = page.locator("[name=codes-0-code]")
        code_input.scroll_into_view_if_needed()
        code_input.fill(VALID_CODE)
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Bereich wurde gespeichert",
        description=(
            "Der neue Bereich erscheint nun in der Bereichs-Übersicht. Die "
            "Spalten **Jobs** und **Codes** zeigen, wie viele Berufe und Codes "
            "der Bereich hat."
        ),
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(AREA_NAME)
        row = page.locator(
            "tr", has=page.locator("th.field-name a", has_text=AREA_NAME)
        )
        expect(row.locator("td.field-number_codes")).to_have_text("1")
