*****************
Development Tools
*****************

This is a collection of scripts which facilitate the development process.
They are targeted at as much platforms and configurations as possible, but there might be edge cases in which they don’t work as expected.

Installation
============

Install all project dependencies and the local python package with :github-source:`tools/install.sh`::

    ./tools/install.sh [--clean] [--pre-commit]

* ``--clean``: Remove all installed dependencies in the ``.venv/`` and ``node_modules/`` directories as well as compiled
  static files in ``lunes_cms/static/dist/``.
* ``--pre-commit``: Install all :ref:`pre-commit-hooks`

Development Server
==================

Run the inbuilt local webserver with :github-source:`tools/run.sh`::

    ./tools/run.sh [--fast]

**Options:**

* ``--fast``: Skip migrations and translation on startup and just start Django

Translations
============

Perform ``makemessages`` and ``compilemessages`` in one step with :github-source:`tools/translate.sh`::

    ./tools/translate.sh

Resolve merge/rebase conflicts with :github-source:`tools/resolve_translation_conflicts.sh`::

    ./tools/resolve_translation_conflicts.sh

Check whether your translations is up-to-date with :github-source:`tools/check_translations.sh`::

    ./tools/check_translations.sh

Test Data
=========

Import test data into the database :github-source:`tools/load_test_data.sh`::

    ./tools/load_test_data.sh

Documentation
=============

Build this documentation with :github-source:`tools/build_documentation.sh`::

    ./tools/build_documentation.sh [--clean]

**Options:**

* ``--clean``: Remove all temporary documentation files in the ``docs/src/ref/`` directory
  as well as the compiled html output in ``docs/dist``. Existing outdated documentation files can cause the
  generation script to fail if e.g. source files were added or deleted.
