"""
WSGI config for lunes-cms project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import configparser
import os

from django.core.wsgi import get_wsgi_application


def application(environ, start_response):
    """
    This returns the WSGI callable

    :param environ: The environment variables
    :type environ: dict

    :param start_response: A function which starts the response
    :type start_response: ~collections.abc.Callable

    :return: The WSGI callable
    :rtype: ~django.core.handlers.WSGIHandler
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lunes_cms.core.settings")

    # Read config from config file
    config = configparser.ConfigParser(interpolation=None)
    config.read("/etc/lunes-cms.ini")
    for section in config.sections():
        for KEY, VALUE in config.items(section):
            os.environ.setdefault(f"LUNES_CMS_{KEY.upper()}", VALUE)

    # Read config from environment
    for key in environ:
        if key.startswith("LUNES_CMS_"):
            os.environ[key] = environ[key]

    _application = get_wsgi_application()

    return _application(environ, start_response)
