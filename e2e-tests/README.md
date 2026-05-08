# E2E Tests & User Manual Generator

E2E tests using pytest-playwright that automatically generate a user manual (Markdown + screenshots).

## Setup

```bash
# Install dependencies
.venv/bin/pip install pytest-playwright mkdocs mkdocs-material

# Install Playwright browser
.venv/bin/python -m playwright install chromium
```

## Running tests

```sh
# Start the dev server first: 
./tools/run.sh
```

```bash
# Run all E2E tests headless (generates user_docs/)
pytest e2e-tests/
```
```bash
# With visible browser (for debugging)
pytest e2e-tests/ --headed
```
```bash
# Run a single test
pytest e2e-tests/test_login.py
```

## Building the user manual

```bash
# Build HTML → user_docs_site/
mkdocs build

# Live preview at http://127.0.0.1:8000
mkdocs serve
```

## Writing a new test

```python
import pytest
from playwright.sync_api import Page

@pytest.mark.e2e
def test_my_feature(page: Page, document, base_url: str) -> None:
    with document.step(
        "Open page",
        description=f"Navigate to the following URL: `{base_url}/de/admin/...`",
    ):
        page.goto(f"{base_url}/de/admin/...")

    with document.step(
        "Perform action",
        description="Description of what the user should do.",
    ):
        page.click("...")
```

Each `document.step()` block takes a screenshot after the action and writes it to `user_docs/`.

| Parameter     | Required | Description                                                      |
|---------------|----------|------------------------------------------------------------------|
| `title`       | yes      | Step heading in the generated markdown                           |
| `description` | no       | Explanatory text shown below the heading, before the screenshot  |
| `screenshot`  | no       | Set to `False` to skip the screenshot (default: `True`)          |

## Output

```
user_docs/
├── index.md
├── <testname>.md        # generated
└── screenshots/         # generated
    └── <testname>_step01.png
```
