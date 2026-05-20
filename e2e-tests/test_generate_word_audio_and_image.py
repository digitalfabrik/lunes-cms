"""
E2E test: Wort-Audio und -Bild mit KI generieren — generates user_docs/generate_word_audio_and_image.md
"""

import json
import re
from pathlib import Path
from typing import Callable

import pytest
from playwright.sync_api import Page, Route, expect

from conftest import ASSETS_DIR

JOB_NAME = "Elektriker/-in"
UNIT_NAME = "Elektrowerkzeuge"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Bohrmaschine"
WORD_PLURAL = "Bohrmaschinen"

_MOCK_AUDIO_FILENAME = "test_audio_mock.mp3"
_MOCK_IMAGE_FILENAME = "test_image_mock.png"


def _fulfill_generate_audio(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {
                "message": "Audio generated!",
                "temp_audio_url": f"/media/temp_audio/{_MOCK_AUDIO_FILENAME}",
                "temp_audio_filename": _MOCK_AUDIO_FILENAME,
            }
        ),
    )


def _fulfill_mock_audio_file(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="audio/mpeg",
        body=Path(ASSETS_DIR / "test_sound.mp3").read_bytes(),
    )


def _fulfill_generate_image(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {
                "message": "Image generated!",
                "temp_image_url": f"/media/temp_image/{_MOCK_IMAGE_FILENAME}",
                "temp_image_filename": _MOCK_IMAGE_FILENAME,
            }
        ),
    )


def _fulfill_mock_image_file(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="image/png",
        body=Path(ASSETS_DIR / "drill.png").read_bytes(),
    )


@pytest.mark.e2e
@pytest.mark.xdist_group("vocabulary_management")
def test_generate_word_audio_and_image(
    page: Page,
    document,
    base_url: str,
    login,
    add_job: Callable,
    add_unit: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    add_word: Callable,
    delete_word: Callable,
) -> None:
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)
    add_word(WORD, WORD_PLURAL, UNIT_NAME)

    # Navigate to the word change page to extract the word ID from the URL
    page.goto(f"{base_url}/de/admin/cmsv2/word/")
    page.fill("#searchbar", WORD)
    page.get_by_role("button", name="Suchen").click()
    page.locator("th.field-word a", has_text=re.compile(f"^{WORD}$")).first.click()
    page.wait_for_url(re.compile(r"/word/\d+/change/"))
    word_id = re.search(r"/word/(\d+)/change/", page.url).group(1)

    with document.step(
        "Öffnen Sie ein Wort",
        description="Navigieren Sie zur Wort-Detailseite.",
    ):
        pass

    page.get_by_role("link", name="Generate Audio").scroll_into_view_if_needed()

    with document.step(
        "Audio-Generator öffnen",
        description='Scrollen Sie zum Bereich **„Audio"** und klicken Sie auf den Button **„Generate Audio"**, um zur KI-Audio-Generierung zu gelangen.',
    ):
        page.get_by_role("link", name="Generate Audio").click()
        page.wait_for_url(re.compile(r"/words/\d+/generate-audio"))
        page.route("**/words/generate-audio-via-openai", _fulfill_generate_audio)
        page.route(f"**/temp_audio/{_MOCK_AUDIO_FILENAME}", _fulfill_mock_audio_file)

    with document.step(
        "Audio generieren",
        description='Klicken Sie auf **„Generate Audio"**. Nach kurzer Ladezeit erscheint eine Vorschau des generierten Audios.',
    ):
        with page.expect_response(re.compile(r"generate-audio-via-openai")):
            page.click("#generate_button")
        expect(page.locator("#audio_preview_section")).to_be_visible()

    with document.step(
        "Generiertes Audio speichern",
        description='Klicken Sie auf **„Store to Audio Field"**, um das generierte Audio dauerhaft dem Wort zuzuweisen.',
    ):
        expect(page.locator("#store_button")).to_be_enabled()
        page.click("#store_button")
        expect(page).to_have_url(
            re.compile(rf"{re.escape(base_url)}/de/admin/cmsv2/word/{word_id}/change/")
        )

    page.unroute("**/words/generate-audio-via-openai")
    page.unroute(f"**/temp_audio/{_MOCK_AUDIO_FILENAME}")

    page.get_by_role("link", name="Generate Image").first.scroll_into_view_if_needed()

    with document.step(
        "Zum Bereich Bilder scrollen",
        description='Scrollen Sie auf der Wort-Detailseite zum Bereich **„Bilder"** und klicken Sie auf den Button **„Generate Image"**.',
    ):
        page.get_by_role("link", name="Generate Image").first.click()
        page.wait_for_url(re.compile(r"/words/\d+/generate-image"))
        page.route("**/words/generate-image-via-openai", _fulfill_generate_image)
        page.route(f"**/temp_image/{_MOCK_IMAGE_FILENAME}", _fulfill_mock_image_file)

    with document.step(
        "Bild generieren",
        description='Klicken Sie auf **„Generate Image"**. Nach kurzer Ladezeit erscheint eine Vorschau des generierten Bildes.',
    ):
        with page.expect_response(re.compile(r"generate-image-via-openai")):
            page.click("#generate_button")
        expect(page.locator("#image_preview_section")).to_be_visible()

    with document.step(
        "Generiertes Bild speichern",
        description='Klicken Sie auf **„Store to Image Field"**, um das generierte Bild dauerhaft dem Wort zuzuweisen.',
    ):
        expect(page.locator("#store_button")).to_be_enabled()
        page.click("#store_button")
        expect(page).to_have_url(
            re.compile(rf"{re.escape(base_url)}/de/admin/cmsv2/word/{word_id}/change/")
        )

    page.unroute("**/words/generate-image-via-openai")
    page.unroute(f"**/temp_image/{_MOCK_IMAGE_FILENAME}")

    delete_word(WORD)
    delete_unit(UNIT_NAME)
    delete_job(JOB_NAME)
