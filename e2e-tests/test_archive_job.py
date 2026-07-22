"""
E2E test: Beruf archivieren und wiederherstellen — generates user_docs/archive_job.md

Covers issue #890: a content manager archives a job so it disappears from the
default job list (and the API), finds it again via the archive filter, and
restores it.
"""

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME = "Elektriker/-in"


def _run_action(page: Page, action_value: str) -> None:
    """Select an admin action from the dropdown and click 'Ausführen'."""
    page.evaluate(
        """
        (value) => {
            const select = document.querySelector('select[name=action]');
            select.value = value;
            $(select).trigger('change');
        }
        """,
        action_value,
    )
    page.click("button[name=index][value='0']")


@pytest.mark.e2e
def test_archive_job(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_job: Callable,
    request: pytest.FixtureRequest,
) -> None:
    def cleanup() -> None:
        # The job may be archived when the test fails, so look it up including archived.
        page.goto(f"{base_url}/de/admin/cmsv2/job/?archived=all")
        locator = page.locator("th.field-name a", has_text=JOB_NAME)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    request.addfinalizer(cleanup)
    add_job(JOB_NAME)

    with document.step(
        "Beruf-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Berufe**.",
    ):
        page.goto(f"{base_url}/de/admin/cmsv2/job/")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/")

    page.locator("th.field-name a", has_text=JOB_NAME).scroll_into_view_if_needed()
    page.locator("tr", has=page.locator("th.field-name a", has_text=JOB_NAME)).locator(
        "input[type=checkbox]"
    ).check()
    with document.step(
        "Beruf auswählen",
        description=f'Aktivieren Sie die Checkbox neben dem Beruf **„{JOB_NAME}"**.',
    ):
        pass

    with document.step(
        'Aktion "Ausgewählte Berufe archivieren" ausführen',
        description='Wählen Sie im Aktions-Dropdown **"Ausgewählte Berufe archivieren"** aus und klicken Sie auf **„Ausführen"**.',
    ):
        _run_action(page, "archive_jobs")

    with document.step(
        "Erfolg — Beruf wurde archiviert",
        description=f'Der Beruf **„{JOB_NAME}"** erscheint nicht mehr in der Standard-Übersicht der Berufe.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator("th.field-name a", has_text=JOB_NAME)).to_have_count(0)

    with document.step(
        "Archivierte Berufe anzeigen",
        description='Wählen Sie in der Seitenleiste unter **„archive status"** den Eintrag **„Archived jobs"**, um archivierte Berufe anzuzeigen.',
    ):
        page.goto(f"{base_url}/de/admin/cmsv2/job/?archived=archived")
        expect(page.locator("th.field-name a", has_text=JOB_NAME)).to_be_visible()

    page.locator("tr", has=page.locator("th.field-name a", has_text=JOB_NAME)).locator(
        "input[type=checkbox]"
    ).check()
    with document.step(
        "Beruf wiederherstellen",
        description='Wählen Sie den Beruf aus und führen Sie die Aktion **"Ausgewählte Berufe aus dem Archiv wiederherstellen"** aus.',
    ):
        _run_action(page, "restore_jobs")

    with document.step(
        "Erfolg — Beruf wurde wiederhergestellt",
        description=f'Der Beruf **„{JOB_NAME}"** erscheint wieder in der Standard-Übersicht der Berufe.',
    ):
        page.goto(f"{base_url}/de/admin/cmsv2/job/")
        expect(page.locator("th.field-name a", has_text=JOB_NAME)).to_be_visible()
