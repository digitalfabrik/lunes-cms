*****************
Production Server
*****************

.. highlight:: bash


.. Note::

    This guide explains how to set up a production server on
    `Ubuntu 20.04.3 LTS (Focal Fossa) <https://releases.ubuntu.com/20.04/>`_. Other linux distributions should work just
    fine, but we don't provide detailed instructions for them.


System requirements
===================

    1. Upgrade alls::

        sudo apt update && sudo apt -y upgrade

    2. Install system requirements::

        sudo apt -y install python3-venv python3-pip ffmpeg


Lunes CMS Package
=================

    1. Choose a location for your installation, e.g. ``/opt/lunes-cms/``::

        sudo mkdir /opt/lunes-cms
        sudo chown www-data:www-data /opt/lunes-cms

    2. Create config and log files and set more restrictive permissions::

        sudo touch /var/log/lunes-cms.log /etc/lunes-cms.ini
        sudo chown www-data:www-data /var/log/lunes-cms.log /etc/lunes-cms.ini
        sudo chmod 660 /var/log/lunes-cms.log /etc/lunes-cms.ini

    3. Change to a shell with the permissions of the webserver's user ``www-data``::

        sudo -u www-data bash

    4. Create a virtual environment::

        cd /opt/lunes-cms
        python3 -m venv .venv
        source .venv/bin/activate

    5. Install the Lunes cms inside the virtual environment::

        pip3 install lunes-cms

       .. Note::1

           If you want to set up a test system with the latest changes from the develop branch instead of the main
           branch, use TestPyPI (with the normal PyPI repository a fallback for the dependencies)::

               pip3 install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple lunes-cms

    6. Create a symlink to the :github-source:`lunes_cms/core/wsgi.py` file to facilitate the Apache configuration::

        ln -s $(python -c "from lunes_cms.core import wsgi; print(wsgi.__file__)") .

    7. Set the initial configuration by adding the following to ``/etc/lunes-cms.ini`` (for a full list of all
       possible configuration values, have a look at :github-source:`example-configs/lunes-cms.ini`)::

        [lunes-cms]

        SECRET_KEY = <your-secret-key>
        FCM_KEY = <your-firebase-key>
        BASE_URL = https://cms.lunes-app.de
        LOGFILE = /var/lunes-cms.log

    8. Leave the www-data shell::

        exit


Static Files
============

    1. Create root directories for all static files. It's usually good practise to separate code and data, so e.g.
       create the directory ``/var/www/lunes-cms/`` with the sub-directories ``static`` and ``media``::

        sudo mkdir -p /var/www/lunes-cms/{static,media}

    2. Make the Apache user ``www-data`` owner of these directories::

        sudo chown -R www-data:www-data /var/www/lunes-cms

    3. Add the static directories to the config in ``/etc/lunes-cms.ini``::

        STATIC_ROOT = /var/www/lunes-cms/static
        MEDIA_ROOT = /var/www/lunes-cms/media

    4. Collect static files::

        cd /opt/lunes-cms
        sudo -u www-data bash
        source .venv/bin/activate
        lunes-cms-cli collectstatic
        exit


Webserver
=========

    1. Install an `Apache2 <https://httpd.apache.org/>`_ server with `mod_wsgi <https://modwsgi.readthedocs.io/en/develop/>`_::

        sudo apt -y install apache2 libapache2-mod-wsgi-py3

    2. Enable the ``rewrite`` and ``wsgi``::

        sudo a2enmod rewrite wsgi

    3. Setup a vhost for the lunes-cms by using our example config: :github-source:`example-configs/apache2-lunes-vhost.conf`
       and edit the your domain and the paths for static files.


Database
========

    1. Execute initial migrations::

        cd /opt/lunes-cms
        sudo -u www-data bash
        source .venv/bin/activate
        lunes-cms-cli migrate


Email configuration
===================

    1. Add your SMTP credentials to ``/etc/lunes.ini`` (for the default values, see :github-source:`example-configs/lunes-cms.ini`)::

        EMAIL_HOST = <your-smtp-server>
        EMAIL_HOST_USER = <your-username>
        EMAIL_HOST_PASSWORD = <your-password>
