"""
E2E test: Passwort zurücksetzen — generates user_docs/password_reset.md
"""

import re
from typing import Generator

import pytest
from playwright.sync_api import Page, expect

NEW_PASSWORD = "Lunes-Test-2024!"
TEST_EMAIL = "max.mustermann@berufsschule-musterstadt.de"


@pytest.fixture
def context(browser):
    """Fresh unauthenticated context for testing the password reset flow."""
    ctx = browser.new_context(locale="de-DE")
    yield ctx
    ctx.close()


@pytest.fixture
def password_reset_user() -> Generator[None, None, None]:
    """max.mustermann is provided by the seed fixture (cms/fixtures/test_data.json)
    with email TEST_EMAIL, so the password reset flow needs no extra setup."""
    yield


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
        expect(page.get_by_text("Wir haben eine E-Mail")).to_be_visible()

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
        expect(page.get_by_text("Ihr Passwort wurde zurückgesetzt")).to_be_visible()
