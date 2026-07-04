"""
E2E test: Mehrere Jobs löschen — generates user_docs/bulk_delete_jobs.md
"""

import pytest
from playwright.sync_api import Page, expect

JOB_NAMES = ["Schlosser/-in", "Klempner/-in", "Dachdecker/-in"]


@pytest.mark.e2e
@pytest.mark.xdist_group("vocabulary_management")
def test_bulk_delete_jobs(page: Page, document, base_url: str, login, add_job) -> None:
    for job_name in JOB_NAMES:
        add_job(job_name)

    with document.step(
        "Job-Bereich öffnen",
        description="Klicken Sie im linken Navigationsmenü auf **Berufe**.",
    ):
        page.goto(f"{base_url}/de/admin/cmsv2/job/?all=")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/?all=")

    for job_name in JOB_NAMES:
        page.locator(
            "tr", has=page.locator("th.field-name a", has_text=job_name)
        ).locator("input[type=checkbox]").check()
    page.locator("th.field-name a", has_text=JOB_NAMES[0]).scroll_into_view_if_needed()
    with document.step(
        "Berufe auswählen",
        description=f'Aktivieren Sie die Checkboxen neben den Berufe **„{JOB_NAMES[0]}"**, **„{JOB_NAMES[1]}"** und **„{JOB_NAMES[2]}"**.',
    ):
        pass

    page.locator("button[name=index][value='0']").scroll_into_view_if_needed()
    page.evaluate("""
        const select = document.querySelector('select[name=action]');
        select.value = 'delete_selected';
        $(select).trigger('change');
    """)
    with document.step(
        'Aktion "Ausgewählte Berufe löschen" auswählen und ausführen',
        description='Wählen Sie im Aktions-Dropdown **"Ausgewählte Berufe löschen"** aus und klicken Sie auf **„Ausführen"**.',
    ):
        page.click("button[name=index][value='0']")

    with document.step(
        "Löschung prüfen und bestätigen",
        description='Prüfen Sie die Liste der ausgewählten Berufe und die Zusammenfassung. Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin mir sicher"**.',
    ):
        selected_objects = page.locator("#content-main > ol")
        expect(page.locator("#content-main > ol > li")).to_have_count(len(JOB_NAMES))
        for job_name in JOB_NAMES:
            expect(selected_objects.get_by_text(job_name, exact=True)).to_be_visible()

        summary_table = page.locator("#content-main table.table-striped")
        expect(page.get_by_role("heading", name="Zusammenfassung")).to_be_visible()
        expect(
            summary_table.locator("tr", has=page.get_by_text("Berufe", exact=True))
            .locator("td")
            .nth(1)
        ).to_have_text(str(len(JOB_NAMES)))
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/job/?all=")

    with document.step(
        "Erfolg — Berufe wurden gelöscht",
        description="Alle drei Berufe sind nicht mehr in der Übersicht vorhanden.",
    ):
        for job_name in JOB_NAMES:
            expect(page.locator("th.field-name a", has_text=job_name)).to_have_count(0)
