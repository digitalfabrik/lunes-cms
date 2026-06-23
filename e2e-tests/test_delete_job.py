"""
E2E test: Job löschen — generates user_docs/delete_job.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

JOB_NAME = "Reinigungskraft"


@pytest.mark.e2e
def test_delete_job(
    page: Page, document, base_url: str, login, add_job: Callable
) -> None:
    add_job(JOB_NAME)

    with document.step(
        "Berufe-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Berufe**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/job/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/")

    page.get_by_role("link", name=JOB_NAME, exact=True).scroll_into_view_if_needed()
    with document.step(
        "Beruf öffnen",
        description=f'Klicken Sie auf den Beruf **„{JOB_NAME}"** in der Liste.',
    ):
        page.get_by_role("link", name=JOB_NAME, exact=True).first.click()

    with document.step(
        "Beruf löschen",
        description='Klicken Sie rechts auf **„Löschen"**.',
    ):
        page.get_by_role("link", name="Löschen").scroll_into_view_if_needed()
        page.get_by_role("link", name="Löschen").click()

    with document.step(
        "Löschung bestätigen",
        description='Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/")
        expect(page.locator("th.field-name a", has_text=JOB_NAME)).to_have_count(0)
