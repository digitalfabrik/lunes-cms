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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Page

DOCS_DIR = Path(__file__).parent.parent / "user_docs"
SCREENSHOTS_DIR = DOCS_DIR / "screenshots"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "e2e: end-to-end test that generates user manual entries")


@pytest.fixture(scope="session", autouse=True)
def prepare_output_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def base_url() -> str:  # type: ignore[override]
    return "http://localhost:8080"


@dataclass
class DocPage:
    """Collects documented steps and writes them as a markdown user manual page."""

    page: Page
    title: str
    filename: str
    _steps: list[dict] = field(default_factory=list)

    @contextlib.contextmanager
    def step(self, title: str, description: str = "", screenshot: bool = True) -> Generator[None, None, None]:
        """Context manager for a documented step. Takes a screenshot after the block."""
        yield
        step_data: dict = {"title": title, "description": description}
        if screenshot:
            idx = len(self._steps) + 1
            img_name = f"{self.filename}_step{idx:02d}.png"
            self.page.screenshot(path=str(SCREENSHOTS_DIR / img_name), full_page=False)
            step_data["screenshot"] = f"screenshots/{img_name}"
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
def document(page: Page, request: pytest.FixtureRequest) -> Generator[DocPage, None, None]:
    """
    Fixture that provides a DocPage for generating user manual entries.
    Writes <test_name>.md + screenshots to user_docs/ after the test.
    """
    import re
    filename = re.sub(r"\[.*?\]", "", request.node.name.removeprefix("test_")).strip("_")
    title = filename.replace("_", " ").title()
    doc = DocPage(page=page, title=title, filename=filename)
    yield doc
    doc.save()
