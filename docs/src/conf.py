from __future__ import annotations

import importlib
import inspect

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import date

from django import VERSION as _django_version_info

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------


# Append project source directory to path environment variable
sys.path.append(os.path.abspath(".."))
# Append sphinx source directory to path environment variable to allow documentation for this file
sys.path.append(os.path.abspath("."))
#: The path to the django settings module (see :doc:`sphinxcontrib-django:readme`)
django_settings = "lunes_cms.core.settings"
#: The "major.minor" version of Django
django_version = f"{_django_version_info[0]}.{_django_version_info[1]}"


# -- Project information -----------------------------------------------------

#: The project name
project = "lunes-cms"
#: The copyright notice
copyright = "Tür an Tür – Digitalfabrik gGmbH"
#: The project author
author = "Lunes"
#: The full version, including alpha/beta/rc tags
from importlib.metadata import version as get_version

release = get_version("lunes-cms")
#: GitHub username
github_username = "digitalfabrik"
#: GitHub repository name
github_repository = "lunes-cms"
#: GitHub URL
github_url = f"https://github.com/{github_username}/{github_repository}"
# GitHub URL of Django repository
django_github_url = f"https://github.com/django/django/blob/stable/{django_version}.x"


# -- General configuration ---------------------------------------------------

#: All enabled sphinx extensions (see :ref:`sphinx-extensions`)
extensions = [
    "sphinx.ext.extlinks",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "sphinxcontrib_django",
]
#: Enable cross-references to other documentations
intersphinx_mapping = {
    "django": (
        f"https://docs.djangoproject.com/en/{django_version}/",
        f"https://docs.djangoproject.com/en/{django_version}/_objects/",
    ),
    "pytest-django": ("https://pytest-django.readthedocs.io/en/latest/", None),
    "python": (
        f"https://docs.python.org/{sys.version_info.major}.{sys.version_info.minor}/",
        None,
    ),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    "sphinx-rtd-theme": (
        "https://sphinx-rtd-theme.readthedocs.io/en/latest/",
        None,
    ),
    "sphinxcontrib-django": (
        "https://sphinxcontrib-django.readthedocs.io/en/latest/",
        None,
    ),
    "setuptools": ("https://setuptools.pypa.io/en/latest/", None),
    "twine": ("https://twine.readthedocs.io/en/latest/", None),
    "wsgi": ("https://wsgi.readthedocs.io/en/latest/", None),
}
#: The number of seconds for timeout. The default is None, meaning do not timeout.
intersphinx_timeout = 5
#: Render type hints with their fully qualified path for readability.
autodoc_typehints_format = "fully-qualified"
#: Several models (e.g. ``Discipline``) are both defined in a submodule and
#: re-exported from their package's ``__init__.py``, so autodoc documents them
#: as two separate objects. Self-referential fields (e.g. MPTT's ``parent``)
#: then produce a short ``~Discipline`` cross-reference that matches both by
#: suffix and can't be resolved uniquely — harmless, but ``-W`` turns it into
#: a build failure. Suppress just this warning subtype, not others.
suppress_warnings = ["ref.python"]
#: The path for patched template files
templates_path = ["templates"]
#: Markup to shorten external links (see :doc:`sphinx:usage/extensions/extlinks`)
extlinks = {
    "github": (f"{github_url}/%s", None),
    "github-source": (f"{github_url}/blob/develop/%s", None),
    "django-source": (f"{django_github_url}/%s", None),
}
#: A string of reStructuredText that will be included at the end of every source file that is read. Used for substitutions.
rst_epilog = f"""
.. |github-username| replace:: {github_username}
.. |github-repository| replace:: {github_repository}
"""

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

#: The theme to use for HTML and HTML Help pages.
html_theme = "sphinx_rtd_theme"
#: The theme options
html_theme_options = {
    "prev_next_buttons_location": None,
}
#: Static files
html_static_path = ["static"]
#: Custom css files
html_css_files = [
    "custom.css",
]
#: Additional template context
html_context = {"current_year": date.today().year}
#: The logo shown in the menu bar
html_logo = "../../lunes_cms/static/images/logo-lunes-dark.svg"
#: The favicon of the html doc files
html_favicon = "../../lunes_cms/static/images/logo.svg"
#: Do not include links to the documentation source (.rst files) in build
html_show_sourcelink = False
#: Do not include a link to sphinx
html_show_sphinx = False
#: Include last updated timestamp
html_last_updated_fmt = "%b %d, %Y"


# -- Source Code links to GitHub ---------------------------------------------


def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
    """
    This function adds source code links to all modules (see :mod:`sphinx:sphinx.ext.linkcode`).
    It links all classes and functions to their source files on GitHub including line numbers.

    :param domain: The programming language of the given object (e.g. ``py``, ``c``, ``cpp`` or ``javascript``)
    :type domain: str

    :param info: Information about the given object. For a python object, it has the keys ``module`` and ``fullname``.
    :type info: dict

    :return: The URL of the given module on GitHub
    :rtype: str
    """
    module_str = info["module"]
    if domain != "py" or not module_str:
        return None
    item = importlib.import_module(module_str)
    line_number_reference = ""
    for piece in info["fullname"].split("."):
        item = getattr(item, piece)
        try:
            line_number_reference = f"#L{inspect.getsourcelines(item)[1]}"
            module_str = item.__module__
        except (TypeError, IOError):
            pass
    module = importlib.import_module(module_str)
    module_path = module_str.replace(".", "/")
    # ``__file__`` is None for namespace packages and some builtin/frozen
    # modules; fall back to an empty filename suffix in that case.
    module_file = module.__file__ or ""
    filename = module_file.partition(module_path)[2]
    if module_str.startswith("django."):
        url = django_github_url
    else:
        url = f"{github_url}/blob/develop"
    return f"{url}/{module_path}{filename}{line_number_reference}"
