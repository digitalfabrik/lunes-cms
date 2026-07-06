**********************
Image Generation
**********************

Lunes can generate vocabulary images via the OpenAI image API. The vocabulary
admin can trigger it per word, and images are generated automatically in the
background for words created through the CSV import.

This requires an API key; without it the feature is simply disabled (a warning
is logged on startup) and everything else keeps working.

The on-demand admin view and the background worker share the same prompt, model
and quality settings, so a manually generated image and an import-generated one
are produced the same way.

Background worker
=================

The database itself is the queue: a ``Word`` with an empty ``image`` field is
considered "pending". After a successful CSV import, a background worker thread
picks up the rows that import just created, calls the OpenAI image API and saves
the files.

The drain is scoped to the word IDs of that import, so an import only generates
images for its own rows. The work is idempotent (already-populated rows are
skipped) and isolates failures per row, so a single failing word does not block
the rest. Generated files are stored under a UUID name by the field's
``upload_to`` — the same convention as every other image in the system.

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
     - OpenAI API key (required to enable image generation)
   * - ``LUNES_CMS_OPENAI_IMAGE_MODEL``
     - ``gpt-image-2``
     - Model used for word image generation
   * - ``LUNES_CMS_OPENAI_IMAGE_QUALITY``
     - ``low``
     - Image quality tier (``low`` / ``medium`` / ``high``)
