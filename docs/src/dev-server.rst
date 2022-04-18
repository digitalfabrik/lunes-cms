******************
Development Server
******************

Run the inbuilt local webserver with :github-source:`tools/run.sh`::

    ./tools/run.sh

This is a convenience script which also performs the following actions:

* Activate the virtual environment
* Migrate database
* Import test data on first start
* Regenerate and compile translation file

If you want to speed up this process and don't need the extra functionality, you might also use::

    ./tools/run.sh --fast

or directly::

    source .venv/bin/activate
    lunes-cms-cli runserver localhost:8080

After that, open your browser and navigate to http://localhost:8080/.

.. Note::

    If you want to use another port than ``8080``, start the server with ``lunes-cms-cli`` and choose another port, or edit :github-source:`tools/_functions.sh`.
