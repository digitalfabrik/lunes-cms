"""
E2E test: Mehrere Wörter löschen — generates user_docs/bulk_delete_words.md
"""

from __future__ import annotations

import re
from functools import partial
from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME = "Warentester/-in"
UNIT_NAME = "Hardware"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORDS = [
    ("Abflussrohr", "Abflussrohre"),
    ("Abgasschlauch", "Abgasschläuche"),
    ("Absteckpfahl", "Absteckpfähle"),
]


@pytest.mark.e2e
def test_bulk_delete_words(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_job: Callable,
    add_unit: Callable,
    add_word: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    delete_word: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_job(JOB_NAME))
    request.addfinalizer(lambda: delete_unit(UNIT_NAME))
    for word, _ in WORDS:
        request.addfinalizer(partial(delete_word, word))
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)
    for word, plural in WORDS:
        add_word(word, plural, UNIT_NAME)

    page.locator(
        "a.nav-link[href='/de/admin/cmsv2/word/']"
    ).scroll_into_view_if_needed()
    page.locator("a.nav-link[href='/de/admin/cmsv2/word/']").click()
    expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/word/")
    page.locator(
        "a.nav-link[href='/de/admin/cmsv2/word/']"
    ).scroll_into_view_if_needed()
    with document.step(
        "Vokabel-Bereich öffnen",
        description="Scrollen Sie im linken Navigationsmenü zu **Vokabel** und klicken Sie darauf.",
    ):
        pass

    for word, _ in WORDS:
        page.locator(
            "tr", has=page.locator("th.field-word a", has_text=re.compile(f"^{word}$"))
        ).locator("input[type=checkbox]").check()
    page.locator(
        "th.field-word a", has_text=re.compile(f"^{WORDS[0][0]}$")
    ).scroll_into_view_if_needed()
    with document.step(
        "Vokabeln auswählen",
        description=f'Aktivieren Sie die Checkboxen neben den Vokabeln **„{WORDS[0][0]}"**, **„{WORDS[1][0]}"** und **„{WORDS[2][0]}"**.',
    ):
        pass

    page.locator("button[name=index][value='0']").scroll_into_view_if_needed()
    page.evaluate(
        """
        const select = document.querySelector('select[name=action]');
        select.value = 'delete_selected';
        $(select).trigger('change');
    """
    )
    with document.step(
        'Aktion "Ausgewählte Vokabeln löschen" auswählen und ausführen',
        description='Wählen Sie im Aktions-Dropdown **"Ausgewählte Vokabeln löschen"** aus und klicken Sie auf **„Ausführen"**.',
    ):
        page.click("button[name=index][value='0']")

    with document.step(
        "Löschung prüfen und bestätigen",
        description='Prüfen Sie die Liste der ausgewählten Vokabeln und die Zusammenfassung. Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin mir sicher"**.',
    ):
        selected_objects = page.locator("#content-main > ol")
        expect(page.locator("#content-main > ol > li")).to_have_count(len(WORDS))
        for word, _ in WORDS:
            expect(selected_objects.get_by_text(word)).to_be_visible()

        summary_table = page.locator("#content-main table.table-striped")
        expect(page.get_by_role("heading", name="Zusammenfassung")).to_be_visible()
        expect(
            summary_table.locator("tr", has=page.get_by_text("Vokabel", exact=True))
            .locator("td")
            .nth(1)
        ).to_have_text(str(len(WORDS)))
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/word/")

    with document.step(
        "Erfolg — Vokabeln wurden gelöscht",
        description="Alle drei Vokabeln sind nicht mehr in der Übersicht vorhanden.",
    ):
        for word, _ in WORDS:
            expect(
                page.locator("th.field-word a", has_text=re.compile(f"^{word}$"))
            ).to_have_count(0)
