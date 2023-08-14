*********************
Code Style Guidelines
*********************


.. _black-code-style:

Black
-----

We use the `black <https://github.com/psf/black>`_ coding style, a flavour of `PEP-8 <https://www.python.org/dev/peps/pep-0008/>`_ for Python.

We use a `pre-commit-hook <https://pre-commit.com/>`_ to apply this style before committing, so you don't have to bother about formatting.
Just code how you feel comfortable and let the tool do the work for you (see :ref:`pre-commit-hooks`).

If you want to apply the formatting without committing, use our developer tool :github-source:`tools/black.sh`::

    ./tools/black.sh


.. _pylint:

Linting
-------

In addition to black, we use pylint to check the code for semantic correctness.
Run pylint with our developer tool :github-source:`tools/pylint.sh`::

    ./tools/pylint.sh

When you think a warning is a false positive, add a comment before the specific line::

    # pylint: disable=unused-argument
    def some_function(*args, **kwargs)

.. Note::

    Please use the string identifiers (``unused-argument``) instead of the alphanumeric code (``W0613``) when disabling warnings.
