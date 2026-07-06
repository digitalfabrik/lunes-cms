****************
Release Workflow
****************

.. highlight:: bash

This document describes the release process for Lunes CMS.
Releases follow a `calendar versioning <https://calver.org/>`__ scheme: ``YYYY.M.N``
(year, month, counter within that month).
The version is stored in ``version.json`` at the repository root and derived dynamically
from the Git tag at build time via
`setuptools-scm <https://github.com/pypa/setuptools_scm>`__.


Overview
========

The release process consists of two separate CircleCI workflows that are triggered manually
via pipeline parameters:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Workflow
     - Purpose
   * - ``delivery_beta``
     - Bumps the version, runs tests, publishes a beta package to TestPyPI,
       creates a GitHub pre-release, generates and commits the SBOM, deploys the user manual.
   * - ``promotion``
     - Publishes the final package to PyPI, promotes the GitHub pre-release to latest,
       notifies Mattermost.


Beta Delivery
=============

Trigger the ``delivery_beta`` workflow from the CircleCI UI by setting the
``run_delivery_beta`` pipeline parameter to ``true``.

The workflow runs the following steps in order:

1. **bump-version** — Calculates the next calendar version using ``app-toolbelt``,
   commits ``version.json`` via the Deliverino GitHub App, and creates the Git tag.

2. **install** — Installs the package after the tag exists so that ``setuptools-scm``
   picks up the correct version.

3. **e2e** — Runs the end-to-end test suite and generates the user manual docs.

4. **build-package** — Builds the Python source distribution and wheel.

5. **publish-beta-package** — Uploads the package to
   `TestPyPI <https://test.pypi.org/project/lunes-cms/>`__ (context: ``pypi-test``).

6. **deploy-user-manual** — Deploys the generated docs to GitHub Pages
   (branch ``gh-pages-user-docs``).

7. **create-release** — Creates a GitHub pre-release for the new tag with auto-generated
   release notes from GitHub (based on ``.github/release.yml``), uploads the built artifact
   as a release asset, generates and commits the Software Bill of Materials (SBOM) via
   ``app-toolbelt``, and notifies Mattermost (context: ``deliverino``).

8. Server installation: Can be triggered manually by doing ``sudo salt-call state.highstate`` on the ``lunes-test.tuerantuer.org`` or it will be installed every night at 2am automatically.



Promotion
=========
IMPORTANT: If there are multiple beta release (pre-releases), the promotion workflow will promote the version that is listed in the ``version.json``. So check which version is on the branch where you trigger the promotion. On main it should be usually the latest beta release.
Once the beta has been validated, trigger the ``promotion`` workflow from the CircleCI UI
by setting the ``run_promotion`` pipeline parameter to ``true``.

The workflow runs the following steps in order:

1. **publish-release-artifact** — Downloads the artifact directly from the GitHub
   pre-release and uploads it to `PyPI <https://pypi.org/project/lunes-cms/>`__
   (context: ``pypi``). This ensures the exact same artifact that was tested in beta
   reaches production.

2. **promote-release** — Promotes the GitHub pre-release to the latest stable release
   using ``app-toolbelt`` and notifies Mattermost (context: ``deliverino``).
3. Server installation: A renovate PR will be created within an hour (triggered 5 past full hour, every hour) here: ``https://git.tuerantuer.org/DF/salt/pulls``. The PR has to approved and merged. Then the highstate will be automatically triggered on the production server.

Create a Hotfix Release
=======================

1. Apply the Fix to the Hotfix Branch
--------------------------------------

- Create an issue for the bug.
- Get the latest tags::

    git tag --sort=-creatordate | head -5

- Create a hotfix branch from the release tag you want to fix.
  The branch name **must start with** ``hotfix`` (e.g. ``hotfix-2025.6.5``)::

    git checkout -b hotfix-2025.6.5 2025.6.4-all

- Create the commits with the particular issue number prefix.
- Push the hotfix branch.
- Create a draft PR for reviews.
- Trigger a beta delivery from this branch.

Required CircleCI Contexts
==========================

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Context
     - Variables
   * - ``deliverino``
     - ``DELIVERINO_PRIVATE_KEY`` — base64-encoded PEM private key of the Deliverino
       GitHub App (App ID ``59249``).
   * - ``pypi-test``
     - ``TWINE_USERNAME``, ``TWINE_PASSWORD``, ``TWINE_REPOSITORY_URL``
       pointing to ``https://test.pypi.org/legacy/``.
   * - ``pypi``
     - ``TWINE_USERNAME``, ``TWINE_PASSWORD`` for the real PyPI.
   * - ``deliverino`` (also used for Mattermost)
     - ``MM_WEBHOOK`` — incoming webhook URL for the Mattermost ``#releases`` channel
       (in addition to ``DELIVERINO_PRIVATE_KEY``).


Versioning Details
==================

The version is calculated automatically by
`app-toolbelt <https://github.com/digitalfabrik/app-toolbelt>`__::

    npx --no app-toolbelt v0 version calc

The result follows the pattern ``YYYY.M.N`` where ``N`` resets to ``0`` at the start
of each new month and increments by one for every release within the same month.

The calculated version is then written to ``version.json`` and committed via
``app-toolbelt v0 release bump-to``, which also creates the Git tag::

    {"versionName":"2026.6.0"}

``pyproject.toml``, ``lunes_cms/__init__.py`` and ``docs/src/conf.py`` read the version
dynamically from the Git tag at build/install time via ``setuptools-scm`` and
``importlib.metadata`` — no manual version file updates needed.
