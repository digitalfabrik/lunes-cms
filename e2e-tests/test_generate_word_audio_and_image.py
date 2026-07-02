"""
E2E test: Wort-Audio und -Bild mit KI generieren — generates user_docs/generate_word_audio_and_image.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

import pytest
from conftest import ASSETS_DIR, DocPage
from playwright.sync_api import expect, Page, Route

JOB_NAME = "Elektriker/-in"
UNIT_NAME = "Elektrowerkzeuge"
UNIT_DESCRIPTION = f"Vokabeln zu {UNIT_NAME}"
WORD = "Bohrmaschine"
WORD_PLURAL = "Bohrmaschinen"

_MOCK_AUDIO_FILENAME = "test_audio_mock.mp3"
_MOCK_IMAGE_FILENAME = "test_image_mock.png"

# The word audio and image (re)generation now happen inline on the word change
# page: each widget posts to its generate endpoint, shows the new asset next to
# the current one, and the user keeps or discards it without leaving the page.
_AUDIO_WIDGET = '.inline-regenerate[data-generate-url*="generate-audio-via-openai"]'
_IMAGE_WIDGET = '.inline-regenerate[data-generate-url*="generate-image-via-openai"]'


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


def _fulfill_store_success(route: Route) -> None:
    route.fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps({"status": "success", "message": "Saved!"}),
    )


@pytest.mark.e2e
def test_generate_word_audio_and_image(
    page: Page,
    document: DocPage,
    base_url: str,
    login: None,
    add_job: Callable,
    add_unit: Callable,
    delete_unit: Callable,
    delete_job: Callable,
    add_word: Callable,
    delete_word: Callable,
    request: pytest.FixtureRequest,
) -> None:
    def _cleanup_routes() -> None:
        page.unroute("**/words/generate-audio-via-openai")
        page.unroute(f"**/temp_audio/{_MOCK_AUDIO_FILENAME}")
        page.unroute("**/store-generated-audio-permanently")
        page.unroute("**/words/generate-image-via-openai")
        page.unroute(f"**/temp_image/{_MOCK_IMAGE_FILENAME}")
        page.unroute("**/store-generated-image-permanently")

    request.addfinalizer(lambda: delete_job(JOB_NAME))
    request.addfinalizer(lambda: delete_unit(UNIT_NAME))
    request.addfinalizer(lambda: delete_word(WORD))
    request.addfinalizer(_cleanup_routes)
    add_job(JOB_NAME)
    add_unit(UNIT_NAME, UNIT_DESCRIPTION, JOB_NAME)
    add_word(WORD, WORD_PLURAL, UNIT_NAME)

    # Navigate to the word change page to extract the word ID from the URL
    page.goto(f"{base_url}/de/admin/cmsv2/word/")
    page.fill("#searchbar", WORD)
    page.get_by_role("button", name="Suchen").click()
    page.locator("th.field-word a", has_text=re.compile(f"^{WORD}$")).first.click()
    page.wait_for_url(re.compile(r"/word/\d+/change/"))
    match = re.search(r"/word/(\d+)/change/", page.url)
    assert match, f"Could not find word ID in URL: {page.url}"
    word_id = match.group(1)
    change_url = re.compile(
        rf"{re.escape(base_url)}/de/admin/cmsv2/word/{word_id}/change/"
    )

    page.route("**/words/generate-audio-via-openai", _fulfill_generate_audio)
    page.route(f"**/temp_audio/{_MOCK_AUDIO_FILENAME}", _fulfill_mock_audio_file)
    page.route("**/store-generated-audio-permanently", _fulfill_store_success)
    page.route("**/words/generate-image-via-openai", _fulfill_generate_image)
    page.route(f"**/temp_image/{_MOCK_IMAGE_FILENAME}", _fulfill_mock_image_file)
    page.route("**/store-generated-image-permanently", _fulfill_store_success)

    audio_widget = page.locator(_AUDIO_WIDGET)
    image_widget = page.locator(_IMAGE_WIDGET)

    with document.step(
        "Öffnen Sie ein Wort",
        description="Navigieren Sie zur Wort-Detailseite.",
    ):
        pass

    audio_widget.scroll_into_view_if_needed()

    with document.step(
        "Audio generieren",
        description='Scrollen Sie zum Bereich **„Audio"** und klicken Sie auf **„Audio generieren"**. Nach kurzer Ladezeit erscheint die Vorschau des generierten Audios neben dem aktuellen.',
    ):
        with page.expect_response(re.compile(r"generate-audio-via-openai")):
            audio_widget.locator(".regen-generate-btn").click()
        expect(audio_widget.locator(".regen-new-preview audio")).to_be_visible()
        expect(audio_widget.locator(".regen-keep-btn")).to_be_enabled()

    with document.step(
        "Generiertes Audio übernehmen",
        description='Klicken Sie auf **„Neues übernehmen"**, um das generierte Audio dauerhaft dem Wort zuzuweisen.',
    ):
        with page.expect_response(re.compile(r"store-generated-audio-permanently")):
            audio_widget.locator(".regen-keep-btn").click()
        expect(page).to_have_url(change_url)

    image_widget.scroll_into_view_if_needed()

    with document.step(
        "Bild generieren",
        description='Scrollen Sie zum Bereich **„Bild"** und klicken Sie auf **„Bild generieren"**. Nach kurzer Ladezeit erscheint die Vorschau des generierten Bildes neben dem aktuellen.',
    ):
        with page.expect_response(re.compile(r"generate-image-via-openai")):
            image_widget.locator(".regen-generate-btn").click()
        expect(image_widget.locator(".regen-new-preview img")).to_be_visible()
        expect(image_widget.locator(".regen-keep-btn")).to_be_enabled()

    with document.step(
        "Generiertes Bild übernehmen",
        description='Klicken Sie auf **„Neues übernehmen"**, um das generierte Bild dauerhaft dem Wort zuzuweisen.',
    ):
        with page.expect_response(re.compile(r"store-generated-image-permanently")):
            image_widget.locator(".regen-keep-btn").click()
        expect(page).to_have_url(change_url)
