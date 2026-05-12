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

OpenAI audio generation
=======================

The vocabulary admin can generate pronunciation audio via OpenAI text-to-speech,
and audio is generated automatically in the background for words created through
the CSV import. This requires an API key; without it the feature is simply
disabled (a warning is logged on startup) and everything else keeps working.

Configure via environment variables:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Variable
     - Default
     - Description
   * - ``LUNES_CMS_OPENAI_API_KEY``
     - –
     - OpenAI API key (required to enable audio generation)
   * - ``LUNES_CMS_OPENAI_TTS_WORD_MODEL``
     - ``tts-1-hd``
     - Model used for single word/term audio
   * - ``LUNES_CMS_OPENAI_TTS_SENTENCE_MODEL``
     - ``gpt-4o-mini-tts``
     - Model used for example-sentence audio
   * - ``LUNES_CMS_OPENAI_TTS_VOICE``
     - ``nova``
     - Voice used for text-to-speech
