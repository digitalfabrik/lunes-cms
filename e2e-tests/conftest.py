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
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generator

import pytest
from playwright.sync_api import Page, expect

DOCS_DIR = Path(__file__).parent.parent / "user_docs"
SCREENSHOTS_DIR = DOCS_DIR / "screenshots"
ASSETS_DIR = Path(__file__).parent / "assets"
REPO_ROOT = Path(__file__).parent.parent


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
    config.addinivalue_line(
        "markers", "xdist_group: group tests to run on the same xdist worker"
    )


@pytest.fixture(scope="session", autouse=True)
def prepare_output_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def base_url() -> str:
    return "http://localhost:8080"



@pytest.fixture
def login(page: Page, base_url: str) -> None:
    """Logs into the CMS admin. Declare as a test dependency to ensure authentication."""
    page.goto(f"{base_url}")
    page.fill("[name=username]", "lunes")
    page.fill("[name=password]", "lunes")
    page.click("[type=submit]")
    page.wait_for_url(f"{base_url}/en/admin/")



@pytest.fixture
def add_job(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that creates a job by name from the CMS admin.
    Asserts the job does not already exist before creating it."""
    def _add(job_name: str) -> None:
        page.goto(f"{base_url}/en/admin/cmsv2/job/")
        page.fill("#searchbar", job_name)
        page.get_by_role("button", name="Search").click()
        expect(page.locator("th.field-name a", has_text=job_name)).to_have_count(0)
        page.goto(f"{base_url}/en/admin/cmsv2/job/add/")
        page.fill("[name=name]", job_name)
        page.set_input_files("[name=icon]", str(ASSETS_DIR / "tester.png"))
        page.click("[name=_save]")

    return _add


@pytest.fixture
def add_unit(page: Page, base_url: str) -> Callable[[str, str, str], None]:
    """Returns a function that creates a unit by title, description and job name.
    Asserts the unit does not already exist before creating it."""
    def _add(title: str, description: str, job_name: str) -> None:
        page.goto(f"{base_url}/en/admin/cmsv2/unit/")
        page.fill("#searchbar", title)
        page.get_by_role("button", name="Search").click()
        expect(page.locator("th.field-title a", has_text=title)).to_have_count(0)
        page.goto(f"{base_url}/en/admin/cmsv2/unit/add/")
        page.fill("[name=title]", title)
        page.fill("[name=description]", description)
        page.locator("#id_jobs").select_option(label=job_name, force=True)
        page.click("[name=_save]")

    return _add


@pytest.fixture
def delete_unit(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a unit by title from the CMS admin."""
    def _delete(title: str) -> None:
        page.goto(f"{base_url}/en/admin/cmsv2/unit/")
        page.locator("th.field-title a", has_text=title).first.click()
        page.get_by_role("link", name="Delete").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def delete_job(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a job by name from the CMS admin."""
    def _delete(job_name: str) -> None:
        page.goto(f"{base_url}/en/admin/cmsv2/job/")
        page.locator("th.field-name a", has_text=job_name).first.click()
        page.get_by_role("link", name="Delete").click()
        page.locator("input[type=submit]").click()

    return _delete


@pytest.fixture
def delete_word(page: Page, base_url: str) -> Callable[[str], None]:
    """Returns a function that deletes a word by its singular form from the CMS admin."""
    def _delete(word: str) -> None:
        page.goto(f"{base_url}/en/admin/cmsv2/word/")
        page.fill("#searchbar", word)
        page.get_by_role("button", name="Search").click()
        page.locator("th.field-word a", has_text=word).first.click()
        page.get_by_role("link", name="Delete").click()
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
        test_file = Path(request.fspath).relative_to(REPO_ROOT).as_posix()
        take_screenshots = test_file in changed

    doc = DocPage(page=page, title=title, filename=filename, take_screenshots=take_screenshots)
    yield doc
    if take_screenshots:
        doc.save()
