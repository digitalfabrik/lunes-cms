"""
E2E test: Job bearbeiten — generates user_docs/edit_job.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

JOB_NAME = "Gärtner/-in"
RENAMED_JOB_NAME = "Gartengestalter/-in"


@pytest.mark.e2e
@pytest.mark.xdist_group("vocabulary_management")
def test_edit_job(
    page: Page, document, base_url: str, login, add_job: Callable, delete_job: Callable
) -> None:
    add_job(JOB_NAME)

    with document.step(
        "Beruf-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Berufe**.",
    ):
        page.click("a.nav-link[href='/de/admin/cmsv2/job/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/")

    page.locator("th.field-name a", has_text=JOB_NAME).scroll_into_view_if_needed()
    with document.step(
        "Beruf öffnen",
        description=f'Klicken Sie auf den Beruf den Sie editieren wollen z.B. **„{JOB_NAME}"** in der Liste.',
    ):
        page.locator("th.field-name a", has_text=JOB_NAME).click()

    page.fill("#id_name", RENAMED_JOB_NAME)
    with document.step(
        "Beruf umbenennen und speichern",
        description=f'Ändern Sie den Namen im Feld **„Beruf"** auf `{RENAMED_JOB_NAME}` und klicken Sie auf **„Sichern"**.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Beruf wurde aktualisiert",
        description=f'Der umbenannte Beruf **„{RENAMED_JOB_NAME}"** erscheint nun in der Berufs-Übersicht.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(RENAMED_JOB_NAME)
        page.locator(
            "th.field-name a", has_text=RENAMED_JOB_NAME
        ).scroll_into_view_if_needed()
        expect(
            page.locator("th.field-name a", has_text=RENAMED_JOB_NAME)
        ).to_be_visible()

    delete_job(RENAMED_JOB_NAME)
