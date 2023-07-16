***************************
Internationalization (i18n)
***************************

For more detailed information, have a look at the official Django documentation on :doc:`django:topics/i18n/index`.

Hardcoded Strings
=================

Whenever you use hardcoded strings, use english text and encapsulate it with a translation function.

Translation File
================

.. highlight:: bash

After you finished your changes to the code base, run the following command::

    source .venv/bin/activate
    cd lunes_cms
    lunes-cms-cli makemessages -l de

Then, open the file :github-source:`lunes_cms/locale/de/LC_MESSAGES/django.po` and fill in the german translations::

    msgid "Your string"
    msgstr "Deine Zeichenkette"

Compilation
===========

To actually see the translated strings in the backend UI, compile the django.po file as follows::

    source .venv/bin/activate
    cd lunes_cms
    lunes-cms-cli compilemessages

Developer Tools
===============

To do ``makemessages`` and ``compilemessages`` in one step, use :github-source:`tools/translate.sh`::

    ./tools/translate.sh

If you run into merge/rebase conflicts inside the translation file, use :github-source:`tools/resolve_translation_conflicts.sh`::

    ./tools/resolve_translation_conflicts.sh

If you want to check, whether your translations is up-to-date or if there are any actions required, run :github-source:`tools/check_translations.sh`::

    ./tools/check_translations.sh
