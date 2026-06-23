"""
E2E test: Wort hinzufügen — generates user_docs/add_word.md
"""

from typing import Callable

import pytest
from playwright.sync_api import Page, expect

from conftest import ASSETS_DIR

JOB_NAME = "Warentester/-in"
UNIT_NAME = "Hardware"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Maus"
WORD_PLURAL = "Mäuse"
EXAMPLE_SENTENCE = (
    "Die Maus ist ein Eingabegerät zur Steuerung des Mauszeigers auf dem Bildschirm."
)
DEFINITION = "Eingabegerät zur Steuerung des Mauszeigers auf einem Computerbildschirm."
ADDITIONAL_MEANING_1 = "Computermaus"
ADDITIONAL_MEANING_2 = "Zeigegerät"


@pytest.mark.e2e
def test_add_word(
    page: Page,
    document,
    base_url: str,
    login,
    add_job: Callable,
    add_unit: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    delete_word: Callable,
    request: pytest.FixtureRequest,
) -> None:
    request.addfinalizer(lambda: delete_job(JOB_NAME))
    request.addfinalizer(lambda: delete_unit(UNIT_NAME))
    request.addfinalizer(lambda: delete_word(WORD))
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)

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

    with document.step(
        "Neues Wort anlegen",
        description='Klicken Sie oben rechts auf den Button **„Vokabel hinzufügen"**.',
    ):
        page.click("a[href='/de/admin/cmsv2/word/add/']")
        expect(page).to_have_url(f"{base_url}/de/admin/cmsv2/word/add/")

    page.locator("[name=word_type]").select_option(label="Substantiv", force=True)
    page.locator("[name=grammatical_gender]").select_option(
        label="Femininum", force=True
    )
    page.locator("[name=singular_article]").select_option(label="die", force=True)
    page.fill("[name=word]", WORD)
    page.locator("[name=plural_article]").select_option(
        label="die (Plural)", force=True
    )
    page.fill("[name=plural]", WORD_PLURAL)
    with document.step(
        "Vokabel Information ausfüllen",
        description=f'Wählen Sie den Worttyp **„Substantiv"**, das Genus **„Femininum"** und den Artikel **„die"**. Geben Sie **„{WORD}"** im Feld **„Word"** und **„{WORD_PLURAL}"** im Feld **„Plural"** ein.',
    ):
        pass

    page.locator("[name=audio]").scroll_into_view_if_needed()
    page.set_input_files("[name=audio]", str(ASSETS_DIR / "test_sound.mp3"))
    with document.step(
        "Audio hochladen",
        description='Laden Sie unter **„Audio"** eine Audiodatei hoch.',
    ):
        pass

    page.locator("[name=image]").scroll_into_view_if_needed()
    page.set_input_files("[name=image]", str(ASSETS_DIR / "tester.png"))
    with document.step(
        "Image hochladen",
        description='Laden Sie unter **„Bilder"** ein Bild hoch.',
    ):
        pass

    page.fill("[name=example_sentence]", EXAMPLE_SENTENCE)
    page.set_input_files(
        "[name=example_sentence_audio]", str(ASSETS_DIR / "test_sound.mp3")
    )
    with document.step(
        "Beispielsatz eingeben (optional)",
        description=f'Geben Sie im Feld **„Beispielsatz"** einen Beispielsatz ein, z. B. `{EXAMPLE_SENTENCE}`, und laden Sie eine Audiodatei für den Beispielsatz hoch.',
    ):
        pass

    page.locator("[name=definition]").scroll_into_view_if_needed()
    page.fill("[name=definition]", DEFINITION)
    page.fill("[name=additional_meaning_1]", ADDITIONAL_MEANING_1)
    page.fill("[name=additional_meaning_2]", ADDITIONAL_MEANING_2)
    with document.step(
        "Verschiedenes ausfüllen (optional)",
        description=f'Geben Sie im Feld **„Definition"** eine Definition ein. Füllen Sie bei Bedarf auch die Felder **„Zusätzliche Bedeutung 1+2"** aus.',
    ):
        pass

    page.locator("[name='unit_word_relations-0-unit']").scroll_into_view_if_needed()
    page.locator("[name='unit_word_relations-0-unit']").select_option(
        label=UNIT_NAME, force=True
    )
    with document.step(
        "Einheit zuordnen",
        description=f'Wählen Sie im Abschnitt **„Einheit-Wort Beziehungen"** die Einheit **„{UNIT_NAME}"** aus.',
    ):
        pass

    page.locator("[name=_save]").scroll_into_view_if_needed()
    with document.step(
        "Wort speichern",
        description='Klicken Sie auf **„Speichern"**, um das neue Wort zu speichern.',
    ):
        page.click("[name=_save]")

    with document.step(
        "Erfolg — Wort wurde gespeichert",
        description=f'Das Wort **„{WORD}"** erscheint nun in der Wörter-Übersicht.',
    ):
        expect(page.locator(".alert-success")).to_be_visible()
        expect(page.locator(".alert-success")).to_contain_text(WORD)
