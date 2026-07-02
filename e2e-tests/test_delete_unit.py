"""
E2E test: Einheit löschen — generates user_docs/delete_unit.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME = "Köchin/Koch"
UNIT_NAME = "Arbeitssicherheit"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"


@pytest.mark.e2e
def test_delete_unit(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_job: Callable,
    add_unit: Callable,
    delete_job: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_job(JOB_NAME))
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)

    with document.step(
        "Einheit-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Einheit**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/unit/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/")

    with document.step(
        "Einheit öffnen",
        description=f'Klicken Sie auf die Einheit **„{UNIT_NAME}"** in der Liste.',
    ):
        page.locator(
            "th.field-title a", has_text=UNIT_NAME
        ).first.scroll_into_view_if_needed()
        page.locator("th.field-title a", has_text=UNIT_NAME).first.click()

    with document.step(
        "Einheit löschen",
        description='Klicken Sie rechts auf **„Löschen"**.',
    ):
        page.get_by_role("link", name="Löschen").scroll_into_view_if_needed()
        page.get_by_role("link", name="Löschen").click()

    with document.step(
        "Löschung bestätigen",
        description='Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/unit/")
        expect(page.locator("th.field-title a", has_text=UNIT_NAME)).to_have_count(0)
