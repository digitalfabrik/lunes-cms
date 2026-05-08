"""
E2E test: Login-Flow — generates user_docs/login.md
"""

import pytest
from playwright.sync_api import expect, Page


@pytest.mark.e2e
def test_login(page: Page, document, base_url: str) -> None:
    with document.step(
        "Lunes CMS im Browser aufrufen",
        description=f"Rufen Sie folgende URL auf: `{base_url}`",
    ):
        page.goto(f"{base_url}")

    with document.step(
        "Anmeldedaten eingeben",
        description="Geben Sie Ihren Benutzernamen und Ihr Passwort in die entsprechenden Felder ein.",
    ):
        page.fill("[name=username]", "lunes")
        page.fill("[name=password]", "lunes")

    with document.step(
        "Anmelden — Dashboard wird geöffnet",
        description="Klicken Sie auf den Anmelden-Button. Sie werden zum Dashboard weitergeleitet.",
    ):
        page.click("[type=submit]")
        expect(page).not_to_have_url(f"{base_url}/de/admin/login/")
