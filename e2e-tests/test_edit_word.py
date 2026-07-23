"""
E2E test: Wort bearbeiten — generates user_docs/edit_word.md
"""

from __future__ import annotations

from typing import Callable

import pytest
from conftest import DocPage
from playwright.sync_api import expect, Page

JOB_NAME = "Warentester/-in"
UNIT_NAME = "Hardware"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Maus"
WORD_PLURAL = "Mäuse"

WORD_UPDATED = "Bildschirm"
WORD_PLURAL_UPDATED = "Bildschirme"
EXAMPLE_SENTENCE_UPDATED = "Der Bildschirm zeigt alle Informationen des Computers an."
ALTERNATIVE_WORD_UPDATED = "Monitor"


@pytest.mark.e2e
def test_edit_word(
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
    def _delete_word() -> None:
        # delete_word removes every match and is a no-op when none exist, so
        # clean up both names regardless of how far the test got before failing.
        delete_word(WORD)
        delete_word(WORD_UPDATED)

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
    page.locator("th.field-word a", has_text=WORD).first.scroll_into_view_if_needed()
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

    page.locator("[name=alternative_words-0-alt_word]").scroll_into_view_if_needed()
    page.fill("[name=alternative_words-0-alt_word]", ALTERNATIVE_WORD_UPDATED)
    page.locator("[name=alternative_words-0-singular_article]").select_option(
        label="der", force=True
    )
    with document.step(
        "Alternatives Wort anpassen",
        description=f'Geben Sie im Abschnitt **„So heißt das auch"** ein alternatives Wort ein, z. B. **„{ALTERNATIVE_WORD_UPDATED}"** mit dem Artikel **„der"**.',
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
