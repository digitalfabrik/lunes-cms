"""
E2E test: Wort bearbeiten — generates user_docs/edit_word.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

JOB_NAME = "Warentester/-in"
UNIT_NAME = "Hardware"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Maus"
WORD_PLURAL = "Mäuse"

WORD_UPDATED = "Bildschirm"
WORD_PLURAL_UPDATED = "Bildschirme"
EXAMPLE_SENTENCE_UPDATED = "Der Bildschirm zeigt alle Informationen des Computers an."
DEFINITION_UPDATED = "Ausgabegerät zur visuellen Darstellung von Daten eines Computers."
ADDITIONAL_MEANING_1_UPDATED = "Monitor"
ADDITIONAL_MEANING_2_UPDATED = "Display"


@pytest.mark.e2e
def test_edit_word(
    page: Page,
    document,
    base_url: str,
    login,
    add_job: Callable,
    add_unit: Callable,
    add_word: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    delete_word: Callable,
    request: pytest.FixtureRequest,
) -> None:
    def _delete_word() -> None:
        try:
            delete_word(WORD_UPDATED)
        except Exception:
            delete_word(WORD)

    request.addfinalizer(lambda: delete_job(JOB_NAME))
    request.addfinalizer(lambda: delete_unit(UNIT_NAME))
    request.addfinalizer(_delete_word)
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
        description=f'Suchen Sie nach einem Wort z.B. **„{WORD}"** und klicken Sie auf den Eintrag in der Liste.',
    ):
        page.locator("th.field-word a", has_text=WORD).first.click()

    page.locator("[name=word_type]").select_option(label="Substantiv", force=True)
    page.locator("[name=grammatical_gender]").select_option(
        label="Maskulinum", force=True
    )
    page.locator("[name=singular_article]").select_option(label="der", force=True)
    page.fill("[name=word]", WORD_UPDATED)
    page.locator("[name=plural_article]").select_option(
        label="die (Plural)", force=True
    )
    page.fill("[name=plural]", WORD_PLURAL_UPDATED)
    with document.step(
        "Vokabel Information anpassen",
        description=f'Ändern Sie das Genus auf **„Maskulinum"**, den Artikel auf **„der"** und das Wort auf **„{WORD_UPDATED}"** mit Plural **„{WORD_PLURAL_UPDATED}"**.',
    ):
        pass

    page.locator("[name=example_sentence]").scroll_into_view_if_needed()
    page.fill("[name=example_sentence]", EXAMPLE_SENTENCE_UPDATED)
    with document.step(
        "Beispielsatz anpassen",
        description=f"Ändern Sie den Beispielsatz auf `{EXAMPLE_SENTENCE_UPDATED}`.",
    ):
        pass

    page.locator("[name=definition]").scroll_into_view_if_needed()
    page.fill("[name=definition]", DEFINITION_UPDATED)
    page.fill("[name=additional_meaning_1]", ADDITIONAL_MEANING_1_UPDATED)
    page.fill("[name=additional_meaning_2]", ADDITIONAL_MEANING_2_UPDATED)
    with document.step(
        "Verschiedenes anpassen",
        description=f'Ändern Sie die **„Definition"** sowie **„Zusätzliche Bedeutung 1+2"**.',
    ):
        pass

    page.locator("[name=_save]").scroll_into_view_if_needed()
    with document.step(
        "Änderungen speichern",
        description='Klicken Sie auf **„Speichern"**, um die Änderungen zu speichern.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Wort wurde aktualisiert",
        description=f'Das aktualisierte Wort **„{WORD_UPDATED}"** erscheint nun in der Übersicht.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(WORD_UPDATED)
