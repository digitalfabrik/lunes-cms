"""
E2E test configuration and documentation generation fixtures.

Usage in tests:
    def test_something(page, document):
        with document.step("Page aufrufen"):
            page.goto("/")

        with document.step("Formular ausfüllen"):
            page.fill("#field", "value")

After the test, a markdown file is written to user_docs/<test_name>.md.
Run mkdocs to build HTML: mkdocs build
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generator
from urllib.parse import quote

import pytest
from playwright.sync_api import Browser, expect, Page

BASE_URL = "http://localhost:8080"
DOCS_DIR = Path(__file__).parent.parent / "user_docs"
EMAIL_OUTBOX_DIR = Path(
    os.environ.get("LUNES_CMS_EMAIL_FILE_PATH", "/tmp/django-email-outbox")
)
SCREENSHOTS_DIR = DOCS_DIR / "screenshots"
ASSETS_DIR = Path(__file__).parent / "assets"
REPO_ROOT = Path(__file__).parent.parent


def select_autocomplete(page: "Page", field_name: str, label: str) -> None:
    """
    Pick an option from a Django admin select2 autocomplete field.

    ``select_option`` does not work on these widgets: the underlying ``<select>``
    is empty and the options are fetched over AJAX only after the user types.
    So open the select2 container, type the label, and click the matching result.
    """
    select = page.locator(f"select[name='{field_name}']")
    select.scroll_into_view_if_needed()
    select.locator("xpath=following-sibling::span[contains(@class, 'select2')]").click()
    search = page.locator("input.select2-search__field")
    search.fill(label)
    page.locator(".select2-results__option", has_text=label).first.click()


def _changed_test_files() -> set[str]:
    """Returns relative paths of test files with uncommitted changes (modified, staged, or new)."""
    cmds = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    changed: set[str] = set()
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        changed |= set(result.stdout.strip().splitlines())
    return changed


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--generate",
        default="changed",
        choices=["all", "changed"],
        help="Screenshot generation: 'all' regenerates every screenshot, 'changed' only for modified test files (default: changed)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "e2e: end-to-end test that generates user manual entries"
    )


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict,
    browser: Browser,
    base_url: str,
    request: pytest.FixtureRequest,
) -> dict:
    """Embed auth state into every test context."""
    context = browser.new_context(locale="de-DE")
    page = context.new_page()
    page.goto(f"{base_url}/de/admin/login/")
    page.fill("[name=username]", "lunes")
    page.fill("[name=password]", "lunes")
    page.click("[type=submit]")
    page.wait_for_url(f"{base_url}/de/admin/")
    state = context.storage_state()
    context.close()
    return {**browser_context_args, "locale": "de-DE", "storage_state": state}


@pytest.fixture(scope="session", autouse=True)
def prepare_output_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def login(page: Page, base_url: str) -> None:
    """Navigate to the admin dashboard (context already has auth state)."""
    page.goto(f"{base_url}/de/admin/")


@pytest.fixture
def add_job(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that creates a job by name from the CMS admin.
    Asserts the job does not already exist before creating it."""

    def _add(job_name: str) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/job/")
        page.fill("#searchbar", job_name)
        page.get_by_role("button", name="Suchen").click()
        expect(page.locator("th.field-name a", has_text=job_name)).to_have_count(0)
        page.goto(f"{base_url}/de/admin/cmsv2/job/add/")
        page.fill("[name=name]", job_name)
        page.set_input_files("[name=icon]", str(ASSETS_DIR / "tester.png"))
        page.click("[name=_save]")

    return _add


@pytest.fixture
def add_unit(page: Page, base_url: str) -> Callable[[str, str, str], None]:
    """Returns a function that creates a unit by title, description and job name.
    Asserts the unit does not already exist before creating it."""

    def _add(title: str, description: str, job_name: str) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/unit/")
        page.fill("#searchbar", title)
        page.get_by_role("button", name="Suchen").click()
        expect(page.locator("th.field-title a", has_text=title)).to_have_count(0)
        page.goto(f"{base_url}/de/admin/cmsv2/unit/add/")
        page.fill("[name=title]", title)
        page.fill("[name=description]", description)
        page.locator("#id_jobs").select_option(label=job_name, force=True)
        page.click("[name=_save]")

    return _add


@pytest.fixture
def delete_unit(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a unit by title from the CMS admin."""

    def _delete(title: str) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/unit/")
        locator = page.locator("th.field-title a", has_text=title)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def delete_job(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a job by name from the CMS admin."""

    def _delete(job_name: str) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/job/")
        locator = page.locator("th.field-name a", has_text=job_name)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def add_word(page: Page, base_url: str) -> Callable[[str, str, str, str, str], None]:
    """Returns a function that creates a word from the CMS admin.
    Args: word, plural, unit_name, word_type_label, article_label"""

    def _add(
        word: str,
        plural: str,
        unit_name: str,
        word_type_label: str = "Substantiv",
        article_label: str = "die",
    ) -> None:
        page.goto(f"{base_url}/de/admin/cmsv2/word/")
        page.fill("#searchbar", word)
        page.get_by_role("button", name="Suchen").click()
        expect(
            page.locator("th.field-word a", has_text=re.compile(f"^{word}$"))
        ).to_have_count(0)
        page.goto(f"{base_url}/de/admin/cmsv2/word/add/")
        page.locator("[name=word_type]").select_option(
            label=word_type_label, force=True
        )
        page.locator("[name=grammatical_gender]").select_option(
            label="Femininum", force=True
        )
        page.locator("[name=singular_article]").select_option(
            label=article_label, force=True
        )
        page.fill("[name=word]", word)
        page.locator("[name=plural_article]").select_option(
            label="die (Plural)", force=True
        )
        page.fill("[name=plural]", plural)
        page.locator("[name=audio]").scroll_into_view_if_needed()
        page.set_input_files("[name=audio]", str(ASSETS_DIR / "test_sound.mp3"))
        page.locator("[name=image]").scroll_into_view_if_needed()
        page.set_input_files("[name=image]", str(ASSETS_DIR / "tester.png"))
        select_autocomplete(page, "unit_word_relations-0-unit", unit_name)
        page.locator("[name=_save]").scroll_into_view_if_needed()
        page.click("[name=_save]")
        expect(page.locator(".alert-success")).to_be_visible()

    return _add


@pytest.fixture
def delete_word(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a word by its singular form from the CMS admin."""

    def _delete(word: str) -> None:
        matching = page.locator(
            "th.field-word a", has_text=re.compile(f"^{re.escape(word)}$")
        )
        # Delete every match: leftovers from a failed test would otherwise make
        # the next search return multiple rows and break strict-mode locators.
        # goto() waits for load, so count() does not race the search results.
        while True:
            page.goto(f"{base_url}/de/admin/cmsv2/word/?q={quote(word)}")
            if matching.count() == 0:
                return
            matching.first.click()
            page.get_by_role("link", name="Löschen").click()
            page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def add_user(page: Page, base_url: str) -> Callable[[str, str], None]:
    """Returns a function that creates a user from the Django admin.
    Asserts the user does not already exist before creating it."""

    def _add(username: str, password: str) -> None:
        page.goto(f"{base_url}/de/admin/auth/user/")
        page.fill("#searchbar", username)
        page.get_by_role("button", name="Suchen").click()
        expect(page.get_by_role("link", name=username)).to_have_count(0)
        page.goto(f"{base_url}/de/admin/auth/user/add/")
        page.fill("[name=username]", username)
        page.fill("[name=email]", f"{username}@example.com")
        page.fill("[name=password1]", password)
        page.fill("[name=password2]", password)
        page.click("[name=_save]")

    return _add


PERMISSION_GROUPS = [
    (
        "Beruf",
        [
            "Beruf | Can add Job",
            "Beruf | Can change Job",
            "Beruf | Can delete Job",
            "Beruf | Can view Job",
        ],
    ),
    (
        "Einheit-Wort",
        [
            "Einheit-Wort Beziehung | Can add Unit-Word Relation",
            "Einheit-Wort Beziehung | Can change Unit-Word Relation",
            "Einheit-Wort Beziehung | Can delete Unit-Word Relation",
            "Einheit-Wort Beziehung | Can view Unit-Word Relation",
        ],
    ),
    (
        "Einheit",
        [
            "Einheit | Can add Unit",
            "Einheit | Can change Unit",
            "Einheit | Can delete Unit",
            "Einheit | Can view Unit",
        ],
    ),
    (
        "Vokabel",
        [
            "Vokabel | Can add Word",
            "Vokabel | Can change Word",
            "Vokabel | Can delete Word",
            "Vokabel | Can view Word",
        ],
    ),
]


@pytest.fixture
def add_group(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that creates a group with standard permissions from the Django admin."""

    def _add(group_name: str) -> None:
        page.goto(f"{base_url}/de/admin/auth/group/add/")
        page.fill("[name=name]", group_name)
        filter_input = page.locator("#id_permissions_input")
        choose_all = page.locator("#id_permissions_add_all")
        for search_term, _ in PERMISSION_GROUPS:
            filter_input.press_sequentially(search_term)
            page.wait_for_timeout(200)
            choose_all.click()
            filter_input.select_text()
            filter_input.press("Backspace")
            page.wait_for_timeout(200)
        page.get_by_role("button", name="Sichern", exact=True).click()

    return _add


@pytest.fixture
def delete_group(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a group by name from the Django admin."""

    def _delete(group_name: str) -> None:
        page.goto(f"{base_url}/de/admin/auth/group/")
        page.fill("#searchbar", group_name)
        page.get_by_role("button", name="Suchen").click()
        locator = page.get_by_role("link", name=group_name)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def email_outbox() -> Generator[Callable[[], str], None, None]:
    """Clears the email outbox before the test and provides a function to read the latest email body."""
    EMAIL_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    for f in EMAIL_OUTBOX_DIR.glob("*.log"):
        f.unlink()

    def get_latest(timeout: int = 10) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            files = sorted(
                EMAIL_OUTBOX_DIR.glob("*.log"), key=lambda f: f.stat().st_mtime
            )
            if files:
                return files[-1].read_text()
            time.sleep(0.2)
        raise TimeoutError(f"No email appeared in {EMAIL_OUTBOX_DIR} within {timeout}s")

    yield get_latest


@pytest.fixture
def delete_user(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a user by username from the Django admin."""

    def _delete(username: str) -> None:
        page.goto(f"{base_url}/de/admin/auth/user/")
        page.fill("#searchbar", username)
        page.get_by_role("button", name="Suchen").click()
        locator = page.get_by_role("link", name=username)
        if locator.count() == 0:
            return
        locator.first.click()
        page.get_by_role("link", name="Löschen").click()
        page.locator("input[type=submit]").click()

    return _delete


@dataclass
class DocPage:
    """Collects documented steps and writes them as a markdown user manual page."""

    page: Page
    title: str
    filename: str
    take_screenshots: bool = True
    _steps: list[dict] = field(default_factory=list)

    @contextlib.contextmanager
    def step(
        self, title: str, description: str = "", screenshot: bool = True
    ) -> Generator[None, None, None]:
        """Context manager for a documented step. Takes a screenshot before the block."""
        step_data: dict = {"title": title, "description": description}
        if screenshot and self.take_screenshots:
            idx = len(self._steps) + 1
            img_name = f"{self.filename}_step{idx:02d}.png"
            self.page.screenshot(path=str(SCREENSHOTS_DIR / img_name), full_page=False)
            step_data["screenshot"] = f"screenshots/{img_name}"
        yield
        self._steps.append(step_data)

    def save(self) -> None:
        """Write the collected steps to a markdown file in user_docs/."""
        lines: list[str] = [f"# {self.title}\n\n"]
        for i, step in enumerate(self._steps, 1):
            lines.append(f"## Schritt {i}: {step['title']}\n\n")
            if step.get("description"):
                lines.append(f"{step['description']}\n\n")
            if "screenshot" in step:
                lines.append(f"![{step['title']}]({step['screenshot']})\n\n")
        output_path = DOCS_DIR / f"{self.filename}.md"
        output_path.write_text("".join(lines), encoding="utf-8")


@pytest.fixture
def document(
    page: Page, request: pytest.FixtureRequest
) -> Generator[DocPage, None, None]:
    """
    Fixture that provides a DocPage for generating user manual entries.
    Writes <test_name>.md + screenshots to user_docs/ after the test.
    Screenshots are only taken if the test file has uncommitted changes.
    """
    import re

    filename = re.sub(r"\[.*?\]", "", request.node.name.removeprefix("test_")).strip(
        "_"
    )
    title = filename.replace("_", " ").title()

    if request.config.getoption("--generate") == "all":
        take_screenshots = True
    else:
        changed = _changed_test_files()
        test_file = Path(request.path).relative_to(REPO_ROOT).as_posix()
        take_screenshots = test_file in changed

    doc = DocPage(
        page=page, title=title, filename=filename, take_screenshots=take_screenshots
    )
    yield doc
    if take_screenshots:
        doc.save()
