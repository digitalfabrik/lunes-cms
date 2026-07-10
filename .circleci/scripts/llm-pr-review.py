#!/usr/bin/env python3
"""
LLM-based PR review script for CircleCI.

Fetches the PR diff via the GitHub API, sends it to the LiteLLM endpoint
for a Django/lunes-cms-specific review, then posts (or updates) a single
comment on the PR. The step only comments — it never approves or rejects.

This script always exits 0 so that LLM or network failures never block
a merge. Errors are printed to stderr and visible in the CI log.

Required environment variables (injected by CircleCI):
  CIRCLE_PULL_REQUEST      URL of the pull request associated with this
                           build (e.g. https://github.com/org/repo/pull/123),
                           only set when the current branch has an open PR.
                           Not populated for forked-PR builds unless secrets
                           are explicitly passed to fork builds.
  CIRCLE_PROJECT_USERNAME  Repository owner (org or user)
  CIRCLE_PROJECT_REPONAME  Repository name

Required secrets (CircleCI contexts):
  NB_LLM_API_TOKEN         API key for litellm.netzbegruenung.verdigado.net
                           (CircleCI context "digitalfabrik-llm-api")
  DELIVERINO_ACCESS_TOKEN  GitHub App installation access token for the
                           Deliverino app (requested by
                           .circleci/scripts/get_access_token.py, needs the
                           "Pull requests" or "Issues" write permission)
"""

import os
import sys

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_API_URL = "https://api.github.com"
LITELLM_BASE_URL = "https://litellm.netzbegruenung.verdigado.net"
LITELLM_MODEL = "verdigado-think"

COMMENT_MARKER = "<!-- llm-pr-review -->"

# Maximum diff size to send to the LLM (200 KB). Larger diffs are truncated.
MAX_DIFF_BYTES = 200_000

SYSTEM_PROMPT = """
You are a senior Django/Python engineer reviewing a pull request for
lunes-cms, the Django-based content management system behind the Lunes
vocabulary trainer app. The codebase is in the middle of migrating from a
legacy data model (the `cms` app: Discipline/TrainingSet/Document) to a
newer one (the `cmsv2` app: Job/Unit/Word) — both apps run side by side, so
check that changes land in the right one and don't reintroduce v1 patterns
into v2 code.

Analyse the diff and the commit messages and report on:
1. Django correctness:
 - Any model field change (new field, altered verbose_name/on_delete/
   null/blank) must be accompanied by a matching migration; the PR should
   not rely on `makemigrations` being run later. New migration files should
   have a short docstring on the `Migration` class describing intent
   (existing convention in `lunes_cms/*/migrations/`).
 - `on_delete` choices on ForeignKeys matter: flag `CASCADE` on
   relationships to user-generated content (jobs/units/words, feedback,
   etc.) where deleting the referenced row would silently wipe out
   unrelated content — prefer `SET_NULL`/`PROTECT` unless cascading
   deletion is clearly intentional.
 - Any new place that creates a `Job`/`Unit`/`Word` (admin forms, CSV
   import, bulk actions, management commands) should consistently set
   `created_by`, `created_by_user` and `creator_is_admin`, the same way
   `BaseAdmin.save_model` does — don't let a new creation path silently
   skip attribution.
2. Internationalization: new or changed `gettext`/`gettext_lazy` strings
 (`_(...)`) must be reflected in `lunes_cms/locale/de/LC_MESSAGES/django.po`
 with no `#, fuzzy` markers and no empty `msgstr`. If a PR adds/changes
 translatable strings but doesn't touch `django.po`, flag it.
3. Type safety: the codebase is fully type-annotated (mypy + django-stubs).
 Flag new functions/methods missing type hints. `request.user` is typed
 `User | AnonymousUser` by django-stubs — a bare assignment to a `User`-typed
 field needs either a real narrowing check or a `# type: ignore[...]` with a
 one-line comment explaining why the request is guaranteed authenticated
 (existing convention), not a silent or unexplained ignore.
4. Code quality gates: this repo enforces black formatting and pylint at
 10.00/10 (see README badge) via pre-commit. Flag obvious formatting drift
 or unjustified `# pylint: disable=...` comments.
5. Security: file upload validators (`validate_file_extension`,
 `validate_file_size`, `validate_multiple_extensions` for audio/image
 fields) must not be bypassed or weakened. Question any new
 `@csrf_exempt` view. Watch for OpenAI API key or other secrets leaking
 into logs, error messages, or committed example configs. CSV import
 code handles user-supplied column data — check for unsafe assumptions
 about column contents.
6. Testing: new behavior (admin actions, CSV import, API endpoints,
 services) should come with tests under `tests/`. If a PR changes a
 shared function's signature, check that all call sites (including
 tests) were updated, not just the primary caller.
7. Obvious typos in code, comments, file paths, identifiers, and
 documentation. Only flag clear spelling mistakes — do not nitpick
 stylistic word choices.
8. Commit message style. The repository convention (see `git log`) is:
 - First line: `<ticket-number-or-branch-slug>: <short imperative summary>`,
   lowercase after the colon (e.g. "658: fix annotations after rebase",
   "401: Make email address required").
 - Additional context (why the change is necessary) goes after a blank
   line in the body.
 - The commit message must be generally useful: it should clearly
   describe what changed and, in the body, why. Flag messages that are
   vague ("fix stuff", "update"), tautological ("change X to X"), or that
   don't explain a non-obvious change.
 Dependabot commits are exempt from these rules.
9. CircleCI config: `.circleci/config.yml` is auto-generated from
 `.circleci/src/{commands,jobs,workflows}/*.yml` via `circleci config pack`
 (see `npm run circleci:update-config`). Only check it for **consistency**:
 if a PR changes a command/job/workflow file under `.circleci/src/`, verify
 that `.circleci/config.yml` was regenerated and reflects that exact
 change. Do not review `.circleci/config.yml`'s full content on its own —
 it's mechanical output, not hand-written, so treating it as a second,
 duplicate review target adds no value.

Be specific and reference file paths and line numbers where possible.
Be concise. Do not approve or reject — provide comments only.
"""


def require_env(name):
    value = os.environ.get(name)
    if not value:
        print(
            f"Error: required environment variable {name!r} is not set", file=sys.stderr
        )
        sys.exit(0)
    return value


def warn(message):
    print(f"Warning: {message}", file=sys.stderr)


def pr_number_from_url(pull_request_url):
    """
    Extracts the PR number from a CIRCLE_PULL_REQUEST URL, e.g.
    "https://github.com/org/repo/pull/123" -> "123".
    """
    return pull_request_url.rstrip("/").rsplit("/", 1)[-1]


def main():
    # -------------------------------------------------------------------------
    # Step 0: Only act on builds associated with an open pull request
    # -------------------------------------------------------------------------

    pull_request_url = os.environ.get("CIRCLE_PULL_REQUEST", "")
    if not pull_request_url:
        print(
            "Skipping LLM review: no open pull request is associated with this "
            "branch (CIRCLE_PULL_REQUEST is not set)."
        )
        return

    pr_number = pr_number_from_url(pull_request_url)

    # -------------------------------------------------------------------------
    # Step 1: Read environment
    # -------------------------------------------------------------------------

    repo_owner = require_env("CIRCLE_PROJECT_USERNAME")
    repo_name = require_env("CIRCLE_PROJECT_REPONAME")
    nb_llm_api_token = require_env("NB_LLM_API_TOKEN")
    github_token = require_env("DELIVERINO_ACCESS_TOKEN")

    auth_headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # -------------------------------------------------------------------------
    # Step 2: Fetch the PR diff from GitHub
    # -------------------------------------------------------------------------

    pr_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
    print(f"Fetching diff from {pr_url} ...")

    try:
        diff_response = requests.get(
            pr_url,
            headers={**auth_headers, "Accept": "application/vnd.github.v3.diff"},
            timeout=30,
        )
    except requests.RequestException as exc:
        warn(f"Could not reach GitHub API: {exc}")
        return

    if diff_response.status_code != 200:
        warn(
            f"Could not fetch diff (HTTP {diff_response.status_code}): "
            f"{diff_response.text[:200]}"
        )
        return

    diff_text = diff_response.text.strip()
    if not diff_text:
        print("No diff found — skipping LLM review.")
        return

    print(f"Diff fetched ({len(diff_text)} chars).")

    truncated = False
    if len(diff_text.encode()) > MAX_DIFF_BYTES:
        diff_text = diff_text.encode()[:MAX_DIFF_BYTES].decode(errors="replace")
        truncated = True
        print(f"Diff truncated to {MAX_DIFF_BYTES} bytes for LLM input.")

    # -------------------------------------------------------------------------
    # Step 2b: Fetch the PR commit messages from GitHub
    # -------------------------------------------------------------------------

    commits_url = f"{pr_url}/commits"
    print(f"Fetching commits from {commits_url} ...")

    commit_messages_block = ""
    try:
        commits_response = requests.get(
            commits_url,
            headers=auth_headers,
            timeout=30,
        )
        if commits_response.status_code == 200:
            commit_lines = []
            for commit in commits_response.json():
                sha = commit.get("sha", "")[:8]
                message = commit.get("commit", {}).get("message", "").rstrip()
                commit_lines.append(f"--- commit {sha} ---\n{message}")
            if commit_lines:
                commit_messages_block = "\n\n".join(commit_lines)
                print(f"Fetched {len(commit_lines)} commit message(s).")
        else:
            warn(
                f"Could not fetch commits (HTTP {commits_response.status_code}): "
                f"{commits_response.text[:200]}"
            )
    except requests.RequestException as exc:
        warn(f"Could not fetch commits: {exc}")

    # -------------------------------------------------------------------------
    # Step 3: Send diff to LiteLLM
    # -------------------------------------------------------------------------

    chat_url = f"{LITELLM_BASE_URL}/v1/chat/completions"
    print(f"Sending diff to LiteLLM ({LITELLM_MODEL}) ...")

    user_content_parts = []
    if commit_messages_block:
        user_content_parts.append(
            "Commit messages in this PR:\n\n" + commit_messages_block
        )
    user_content_parts.append("Diff:\n\n" + diff_text)
    user_content = "\n\n".join(user_content_parts)
    if truncated:
        user_content += "\n\n[Diff was truncated to 200 KB]"

    try:
        llm_response = requests.post(
            chat_url,
            headers={
                "Authorization": f"Bearer {nb_llm_api_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": LITELLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=300,
        )
    except requests.RequestException as exc:
        warn(f"Could not reach LiteLLM: {exc}")
        return

    if llm_response.status_code != 200:
        warn(
            f"LiteLLM returned HTTP {llm_response.status_code}: "
            f"{llm_response.text[:200]}"
        )
        return

    llm_data = llm_response.json()
    review_text = (
        llm_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    )
    if not review_text:
        warn("LLM returned an empty review.")
        return

    print("LLM review received.")

    # -------------------------------------------------------------------------
    # Step 4: Find existing bot comment (identified by marker)
    # -------------------------------------------------------------------------

    comments_url = (
        f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"
    )
    print("Checking for existing LLM review comment ...")

    try:
        comments_response = requests.get(
            comments_url,
            headers=auth_headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        warn(f"Could not fetch comments: {exc}")
        return

    if comments_response.status_code != 200:
        warn(
            f"Could not fetch comments (HTTP {comments_response.status_code}): "
            f"{comments_response.text[:200]}"
        )
        return

    existing_comment_id = None
    for comment in comments_response.json():
        if COMMENT_MARKER in comment.get("body", ""):
            existing_comment_id = comment["id"]
            break

    # -------------------------------------------------------------------------
    # Step 5: Post or update the comment
    # -------------------------------------------------------------------------

    comment_body = (
        f"{COMMENT_MARKER}\n" f"### LLM Review ({LITELLM_MODEL})\n\n" f"{review_text}\n"
    )

    post_headers = {**auth_headers, "Content-Type": "application/json"}

    try:
        if existing_comment_id:
            update_url = (
                f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}"
                f"/issues/comments/{existing_comment_id}"
            )
            print(f"Updating existing comment {existing_comment_id} ...")
            resp = requests.patch(
                update_url,
                headers=post_headers,
                json={"body": comment_body},
                timeout=30,
            )
        else:
            print("Posting new comment ...")
            resp = requests.post(
                comments_url,
                headers=post_headers,
                json={"body": comment_body},
                timeout=30,
            )
    except requests.RequestException as exc:
        warn(f"Could not post comment: {exc}")
        return

    if resp.status_code not in (200, 201):
        warn(f"Could not post comment (HTTP {resp.status_code}): " f"{resp.text[:200]}")
        return

    print("LLM review comment posted successfully.")


if __name__ == "__main__":
    main()
