***********************
Lunes CMS documentation
***********************

This is the developer documentation for the Lunes Django backend.

.. Note::
    For general help with the Django framework, please refer to the :doc:`django:index`.

.. Note::
    The API usage documentation can be found here: https://lunes.tuerantuer.org/api/docs/


First Steps
===========

.. toctree::
    :caption: First Steps
    :hidden:

    installation
    dev-server

* :doc:`installation`: Installation guide
* :doc:`dev-server`: Run local development server


Deployment
==========

.. toctree::
    :caption: Deployment
    :hidden:

    packaging
    prod-server
    changelog

* :doc:`packaging`: Create an easy installable python
* :doc:`prod-server`: Setup the production server
* :doc:`changelog`: The release history including all relevant changes


Reference
==============

.. toctree::
    :caption: Reference
    :hidden:

    ref/lunes_cms

* :doc:`ref/lunes_cms`: The main of the lunes-cms with the following sub-packages:

  - :doc:`ref/lunes_cms.api`: This is the app which contains all API routes and classes which map the cms models to API JSON responses. This is not the API documentation itself, but the Django developer documentation.
  - :doc:`ref/lunes_cms.cms`: This is the content management system for backend users which contains all database models, views, forms and templates.
  - :doc:`ref/lunes_cms.core`: This is the project's main app which contains all configuration files.
  - :doc:`ref/lunes_cms.help`: This is the app which handles the public upload of images.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
