"""
E2E test: Passwort zurücksetzen — generates user_docs/password_reset.md
"""

import re
from typing import Generator

import pytest
from playwright.sync_api import Browser, Page, expect

NEW_PASSWORD = "Lunes-Test-2024!"
TEST_USERNAME = "max.mustermann"
TEST_EMAIL = "max.mustermann@berufsschule-musterstadt.de"


@pytest.fixture
def context(browser):
    """Fresh unauthenticated context for testing the password reset flow."""
    ctx = browser.new_context(locale="de-DE")
    yield ctx
    ctx.close()


@pytest.fixture
def password_reset_user(
    browser: Browser, browser_context_args: dict, base_url: str
) -> Generator[None, None, None]:
    """Creates max.mustermann with a known email via admin UI, then deletes him."""
    ctx = browser.new_context(**browser_context_args)
    p = ctx.new_page()
    p.goto(f"{base_url}/de/admin/auth/user/add/")
    p.fill("[name=username]", TEST_USERNAME)
    p.fill("[name=password1]", "Lunes-Init-2024!")
    p.fill("[name=password2]", "Lunes-Init-2024!")
    p.click("[name=_save]")
    p.fill("[name=email]", TEST_EMAIL)
    p.click("[name=_save]")
    ctx.close()

    yield

    ctx2 = browser.new_context(**browser_context_args)
    p2 = ctx2.new_page()
    p2.goto(f"{base_url}/de/admin/auth/user/")
    p2.fill("#searchbar", TEST_USERNAME)
    p2.get_by_role("button", name="Suchen").click()
    p2.get_by_role("link", name=TEST_USERNAME).first.click()
    p2.get_by_role("link", name="Löschen").click()
    p2.locator("input[type=submit]").click()
    ctx2.close()


@pytest.mark.e2e
def test_password_reset(
    page: Page, document, base_url: str, email_outbox, password_reset_user
) -> None:
    page.goto(f"{base_url}/de/admin/login/")

    with document.step(
        "Passwort vergessen – Formular aufrufen",
        description='Klicken Sie auf der Anmeldeseite auf "Forgotten your password or username?" oder rufen Sie die Seite direkt auf.',
    ):
        page.get_by_role("link", name="Forgotten your password or username?").click()
        expect(page).to_have_url(f"{base_url}/de/admin/password_reset/")

    with document.step(
        "E-Mail-Adresse eingeben",
        description="Geben Sie Ihre registrierte E-Mail-Adresse ein und klicken Sie auf Absenden.",
    ):
        page.fill("[name=email]", TEST_EMAIL)
        page.click("[type=submit]")
        expect(page).to_have_url(f"{base_url}/de/admin/password_reset/done/")

    with document.step(
        "Bestätigungsseite",
        description="Sie erhalten in Kürze eine E-Mail mit einem Link zum Zurücksetzen Ihres Passworts.",
    ):
        expect(page.locator("h1")).to_be_visible()

    email_body = email_outbox()
    match = re.search(r"(/\w{2}/reset/[\w-]+/[\w-]+/)", email_body)
    assert match, f"No reset link found in email:\n{email_body}"
    reset_path = match.group(1)

    page.goto(f"{base_url}{reset_path}")

    with document.step(
        "Neues Passwort festlegen",
        description="Folgen Sie dem Link in der E-Mail und geben Sie ein neues Passwort ein.",
    ):
        page.fill("[name=new_password1]", NEW_PASSWORD)
        page.fill("[name=new_password2]", NEW_PASSWORD)
        page.click("[type=submit]")
        expect(page).to_have_url(f"{base_url}/de/reset/done/")

    with document.step(
        "Passwort erfolgreich zurückgesetzt",
        description="Ihr Passwort wurde erfolgreich geändert. Sie können sich jetzt mit dem neuen Passwort anmelden.",
    ):
        expect(page.locator("h1")).to_be_visible()
