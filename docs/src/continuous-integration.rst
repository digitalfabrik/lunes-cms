*********************************
Continuous Integration (CircleCI)
*********************************

.. admonition:: What is continuous integration?

   Continuous integration (CI) is a software development strategy that increases the speed of development while ensuring
   the quality of the code that teams deploy. Developers continually commit code in small increments (at least daily, or
   even several times a day), which is then automatically built and tested before it is merged with the shared repository.

   Source: `CircleCI documentation <https://circleci.com/continuous-integration/>`__

Configuration
=============

Our CircleCI configuration resides in :github-source:`.circleci/config.yml`, but that file is
**auto-generated and must not be edited by hand**. It is packed from the sources in
:github-source:`.circleci/src` — one file per command, job and workflow — by running::

    npm run circleci:update-config

which invokes ``circleci config pack`` and validates the result. Change the files under
``.circleci/src/`` and regenerate; a pull request that edits one without the other is
inconsistent.
See `Configuring CircleCI <https://circleci.com/docs/2.0/configuration-reference/>`__ for a full reference.

Which workflow runs is decided by the pipeline parameters declared in
``.circleci/src/@common.yml``. Each workflow has its own ``run_*`` switch, so a workflow other
than ``commit`` is started by triggering a pipeline with that parameter set to ``true`` —
either from the CircleCI UI or through the
`CircleCI API <https://circleci.com/docs/api/v2/#operation/triggerPipeline>`__. Because
``run_commit`` defaults to ``true``, such a trigger normally also sets ``run_commit`` to
``false`` so the ``commit`` workflow does not run a second time.

Workflow ``commit``
===================

This workflow gets triggered on every push to a branch other than ``main``, which in practice
means while a pull request is in progress.

shellcheck/check
----------------

This job makes use of the `ShellCheck CircleCI Orb <https://circleci.com/developer/orbs/orb/circleci/shellcheck>`_ and
executes the pre-defined job ``shellcheck/check``. It is configured to check the directory :github-source:`tools`
and to allow external sources because all dev tools source one common function script.

.. _circleci-install:

install
-------

This job executes ``uv sync --extra dev --locked`` (installing the exact versions pinned in ``uv.lock``) and makes use of the `CircleCI Dependency Cache <https://circleci.com/docs/2.0/caching/>`__.
It passes the virtual environment ``.venv`` to the subsequent jobs.

lint-ts
-------

This job installs the npm dependencies and runs ``npm run lint`` and ``npm run format:check``
to lint and format-check the TypeScript sources.

build-js
--------

This job installs the npm dependencies and runs ``npm run build`` to build the TypeScript
assets.

.. _circleci-compile-translations:

compile-translations
--------------------

This job compiles the translation file and passes the resulting ``django.mo`` to the jobs that
need it.

check-translations
------------------

This job uses the dev-tool :github-source:`tools/check_translations.sh` to check whether the translation file is up to date and
does not contain any empty or fuzzy entries.

black
-----

This job executes ``black --check .``, which checks whether the code matches the :ref:`black-code-style` code style.

isort
-----

This job executes ``isort . --skip-glob "**/migrations/**"``, which checks whether the imports
are ordered consistently. Migrations are excluded because they are generated.

pylint
------

This job executes :github-source:`tools/pylint.sh`, which checks whether :ref:`pylint` throws any errors or warnings.

mypy
----

This job executes :github-source:`tools/mypy.sh`, which checks the static types.

test
----

This job runs the tests on the default Python version. It sets up a temporary postgres database,
checks that no migrations are missing (``makemigrations cms --check``) and runs the migrations
before testing. It runs pytest and passes the coverage report ``coverage.xml`` and the JUnit
results in ``test-results`` to the :ref:`circleci-upload-test-coverage` job and the build
artifacts.

test-python313
--------------

This job runs the same test suite on Python 3.13 against an SQLite backend, to catch
incompatibilities with the newer interpreter early. It is independent of the :ref:`circleci-install`
job and manages its own cache.

.. _circleci-upload-test-coverage:

upload-test-coverage
--------------------

This job uploads the coverage report produced by the ``test`` job to
`Qlty <https://qlty.sh>`__ using the ``qltysh/qlty-orb`` orb.

build-documentation
-------------------

This job checks whether the documentation can be generated without any errors by running
:github-source:`tools/build_documentation.sh`.

Workflow ``commit_main``
========================

This workflow gets executed when a commit is pushed to the ``main`` branch, typically after a
pull request has been merged. In addition to :ref:`circleci-install`, ``build-js`` and
:ref:`circleci-compile-translations` it runs:

bump-version
------------

This job authenticates as the deliverino app, calculates the next version and commits the
version bump.

e2e
---

This job installs the ``e2e`` extra together with ffmpeg and the Playwright Chromium browser,
and runs the end-to-end tests.

.. _circleci-build-package:

build-package
-------------

This job creates a python package and passes the resulting files in ``dist`` to the
:ref:`circleci-publish-package` job. See :doc:`packaging` for more information.

Workflow ``llm_review``
=======================

This workflow runs the LLM-based pull request review. Unlike the other workflows it is
not started by a push: CircleCI cannot subscribe to GitHub's ``pull_request`` event, so
the GitHub Actions workflow :github-source:`.github/workflows/llm-pr-review.yml` reacts
to that event and triggers this workflow through the
`CircleCI API <https://circleci.com/docs/api/v2/#operation/triggerPipeline>`__.

It is triggered when a pull request is opened, reopened, marked ready for review, or
receives a push, and it is skipped for pull requests from forks (which get no secrets).
The trigger passes three pipeline parameters:

* ``run_llm_review`` — ``true``, which selects this workflow.
* ``llm_review_pr_number`` — the number of the pull request to review.
* ``run_commit`` — ``false``, so the ``commit`` workflow does not run a second time
  (its default is ``true``).

The GitHub Actions workflow needs a ``CIRCLECI_API_TOKEN`` repository secret containing
a CircleCI `Personal API Token <https://circleci.com/docs/managing-api-tokens/>`__. It
fails with an explicit error if the secret is missing.

llm-pr-review
-------------

This job runs :github-source:`.circleci/scripts/llm-pr-review.py`, which sends the pull
request's diff, commit messages and labels to the LiteLLM endpoint and posts (or updates)
a single review comment via the deliverino app. It only comments — it never approves,
rejects, or changes labels. The script always exits successfully, so an LLM or network
failure can never block a merge. It needs the ``deliverino`` and
``digitalfabrik-llm-api`` contexts.

Workflows ``delivery_beta`` and ``promotion``
=============================================

These two workflows publish a release and are triggered manually via the ``run_delivery_beta``
and ``run_promotion`` pipeline parameters. ``delivery_beta`` builds and publishes a beta to
TestPyPI, deploys the user manual and creates a GitHub pre-release; ``promotion`` then promotes
that pre-release to a stable release on PyPI.

Both are documented step by step in :doc:`release-workflow`, which is the authoritative
description of the release process.

.. _circleci-publish-package:

publish-package
---------------

This job runs ``twine check`` on the built package and publishes it to
`TestPyPI <https://test.pypi.org/project/lunes-cms/>`__ (or PyPI, for a stable release)
via :doc:`twine:index`.

Debugging with SSH
==================

If you encounter any build failures which you cannot reproduce on your local machine, you can SSH into the build
server and examine the problem. See `Debugging with SSH <https://circleci.com/docs/2.0/ssh-access-jobs/>`__ for
more information.

.. _circleci-unauthorized:

⚠ Unauthorized (CircleCI)
=========================

.. admonition:: Got error "Unauthorized"?
    :class: error

    Some jobs need secrets that are passed into the execution via `contexts <https://circleci.com/docs/2.0/contexts/>`_.
    If you get the error "unauthorized", you have to make sure you have the correct permissions to access these secrets.
