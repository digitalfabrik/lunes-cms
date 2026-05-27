"""
E2E test: Wort löschen — generates user_docs/delete_word.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

JOB_NAME = "Warentester/-in"
UNIT_NAME = "Hardware"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Maus"
WORD_PLURAL = "Mäuse"


@pytest.mark.e2e
@pytest.mark.xdist_group("vocabulary_management")
def test_delete_word(
    page: Page,
    document,
    base_url: str,
    login,
    add_job: Callable,
    add_unit: Callable,
    add_word: Callable,
    delete_unit: Callable,
    delete_job: Callable,
) -> None:
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)
    add_word(WORD, WORD_PLURAL, UNIT_NAME)

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

    page.fill("#searchbar", WORD)
    page.get_by_role("button", name="Suchen").click()
    page.locator("th.field-word a", has_text=WORD).scroll_into_view_if_needed()
    with document.step(
        "Vokabel öffnen",
        description=f'Suchen Sie nach **„{WORD}"** und klicken Sie auf den Eintrag in der Liste.',
    ):
        page.locator("th.field-word a", has_text=WORD).first.click()

    with document.step(
        "Vokabel löschen",
        description='Klicken Sie rechts auf **„Löschen"**.',
    ):
        page.get_by_role("link", name="Löschen").scroll_into_view_if_needed()
        page.get_by_role("link", name="Löschen").click()

    with document.step(
        "Löschung bestätigen",
        description='Bestätigen Sie die Löschung mit einem Klick auf **„Ja, ich bin sicher"**.',
    ):
        page.locator("input[type=submit]").click()
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/word/?q={WORD}")
        expect(page.locator("th.field-word a", has_text=WORD)).to_have_count(0)

    delete_unit(UNIT_NAME)
    delete_job(JOB_NAME)
