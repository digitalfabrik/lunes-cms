************
Installation
************

.. Note::

    If you want to develop on Windows, we suggest using the `Windows Subsystem for Linux <https://docs.microsoft.com/en-us/windows/wsl/>`_ in combination with `Ubuntu <https://ubuntu.com/wsl>`_ and `postgresql <https://wiki.ubuntuusers.de/PostgreSQL/>`__ as local database server.


Development Setup
=================

.. Note::

    This project runs on Django – if you're new to Django it may be worth checking out `Django's getting started guide <https://www.djangoproject.com/start/>`__.

Here's how to get the site running on your machine.

#. Get into a Unix-like environment

    * If you're on Windows, install the Windows Subsystem for Linux. Then execute ``wsl bash`` and continue with the commands below.

    * If you're already on Linux/Mac, no action needed.

#. Clone the repository: ``git clone git@github.com:digitalfabrik/lunes-cms.git``

#. Move into the direcotry: ``cd lunes-cms``

#. Set up virtual environment of choice with a current ``pip`` and ``setuptools`` version. For example (using Debian):

    * ``apt install python3-venv``
    * ``python3 -m venv .venv``
    * ``source .venv/bin/activate``
    * ``pip install -U pip setuptools``
    * ``pip install wheel``

#. Install system dependencies: ``cat requirements.system | xargs sudo apt-get install``

#. Install project dependencies: ``python3 setup.py develop``

#. Set up Django and run the development server:

    * ``vocabulary-trainer migrate``
    * ``vocabulary-trainer createsuperuser``
    * ``vocabulary-trainer runserver``

Now that you've gotten everything set up, to run the development server in
the future, all you'll need to do is activate your virtual environment
(e.g. via ``source .venv/bin/activate`` if you use the instructions above, or
``pipenv shell`` if you're using pipenv) and call ``runserver`` like in the
last command above.


Production Deployment
=====================

#. ``adduser vocabulary-trainer``
#. ``git clone git@github.com:digitalfabrik/lunes-cms.git``
#. ``cd lunes-cms``
#. ``pip install -U pip setuptools``
#. ``cat requirements.system | xargs sudo apt-get``
#. ``python3 setup.py install``
#. Change database settings in ``settings.py``, for example to MySQL or Postgresql. After installation, usually find the ``settings.py`` in the ``/usr/lib/python3.X/site-packages/vocabulary-trainer``
#. ``vocabulary-trainer migrate``
#. ``vocabulary-trainer collectstatic``
#. ``systemctl start vocabulary-trainer.service``
#. Configure Apache2 or Nginx reverse proxy. See provided Apache2 example.