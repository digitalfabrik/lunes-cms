**********************
Audio Generation
**********************

Lunes can generate pronunciation audio for vocabulary via OpenAI
text-to-speech. The vocabulary admin can trigger it per word, and audio is
generated automatically in the background for words created through the CSV
import.

This requires an API key; without it the feature is simply disabled (a warning
is logged on startup) and everything else keeps working.

Background worker
=================

The database itself is the queue: a ``Word`` with an empty ``audio`` field (or
an empty ``example_sentence_audio`` while ``example_sentence`` is set) is
considered "pending". After a successful CSV import, a background worker thread
picks up the rows that import just created, calls OpenAI TTS and saves the
files.

The drain is scoped to the word IDs of that import — it never touches words
created elsewhere, so an import only generates audio for its own rows. The work
is idempotent (already-populated rows are skipped) and isolates failures per
row, so a single failing word does not block the rest.

AI-generated marking
====================

Art. 50 of the EU AI Act requires synthetic audio to be marked in a
machine-readable format. The duty falls on the provider of the generating AI
system, so whether Lunes counts as one is a legal question; the marking is
written so that either way the clips carry it. Every clip generated through
OpenAI TTS (words and example sentences, admin view and CSV-import worker
alike) gets the marking from ``mark_as_ai_generated()`` right after loudness
normalization. It is the same XMP packet the image marking embeds (IPTC
``DigitalSourceType`` ``trainedAlgorithmicMedia``), stored as the XMP
specification prescribes for MP3: in an ID3v2 ``PRIV`` frame owned by ``XMP``.
The audio stream is copied, not re-encoded.

ffmpeg keeps the frame when ``Word.convert_audio()`` re-encodes word audio
afterwards, so the marking is written once, at generation. Anything that
rewrites the file without carrying its tags over strips the marking.

Only clips generated from now on are marked. Existing clips are not
backfilled, and no field records which clips are AI-generated (unlike
``image_source`` for images). Audio uploaded by editors is left untouched.

Configuration
=============

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
   * - ``LUNES_CMS_OPENAI_TTS_MODEL``
     - ``gpt-4o-mini-tts``
     - Model used for all text-to-speech (words and example sentences). Must
       support the ``instructions`` parameter.
   * - ``LUNES_CMS_OPENAI_TTS_VOICE``
     - ``nova``
     - Voice used for text-to-speech
   * - ``LUNES_CMS_OPENAI_TTS_LOUDNESS_LUFS``
     - ``-16.0``
     - Loudness (in LUFS) generated audio is normalized to,
       so all clips play back at a consistent volume
