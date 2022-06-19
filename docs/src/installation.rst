************
Installation
************

.. Note::

    If you want to develop on Windows, we suggest using the `Windows Subsystem for Linux <https://docs.microsoft.com/en-us/windows/wsl/>`_ in combination with `Ubuntu <https://ubuntu.com/wsl>`_.


Prerequisites
=============

Followings are required before installing the project (install them with your manager):

* `git <https://git-scm.com/>`_
* `python3.8 <https://www.python.org/downloads/release/python-380/>`_ or higher
* `python3-pip <https://packages.ubuntu.com/search?keywords=python3-pip>`_ (`Debian-based distributions <https://en.wikipedia.org/wiki/Category:Debian-based_distributions>`_, e.g. `Ubuntu <https://ubuntu.com>`__) / `python-pip <https://www.archlinux.de/packages/extra/x86_64/python-pip>`_ (`Arch-based distributions <https://wiki.archlinux.org/index.php/Arch-based_distributions>`_)
* `python3-venv <https://docs.python.org/3/library/venv.html>`__
* `libpq-dev <https://www.postgresql.org/docs/9.5/libpq.html>`__ to compile `psycopg2 <https://www.psycopg.org/docs/install.html#build-prerequisites>`__
* `gettext <https://www.gnu.org/software/gettext/>`_ and `pcregrep <https://pcre.org/original/doc/html/pcregrep.html>`_ to use the translation features
* `ffmpeg <https://ffmpeg.org/>`_ for audio processing

Download sources
================

.. highlight:: bash

Clone the project, either

.. container:: two-columns

    .. container:: left-side

        via SSH:

        .. parsed-literal::

            git clone git\@github.com:|github-username|/|github-repository|.git
            cd |github-repository|

    .. container:: right-side

        or HTTPS:

        .. parsed-literal::

            git clone \https://github.com/|github-username|/|github-repository|.git
            cd |github-repository|


Install dependencies and local
======================================

And install it using our developer tool :github-source:`tools/install.sh`::

    ./tools/install.sh
