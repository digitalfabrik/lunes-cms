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

AI disclosure label and provenance
==================================

The EU AI Act (Art. 50) requires generated images to be marked as such, so every
prompt ends with an instruction to render the European Commission's
"AI GENERATED" label — a black pill with white uppercase text — into the bottom
right corner of the picture. The default ban on text inside the image
(issue #918) exempts that label explicitly.

Generated images are requested from OpenAI **in the format we serve**
(``webp`` by default) rather than converted afterwards. The stored file is then
byte-for-byte OpenAI's own output, which keeps the provenance markings it
embeds — a C2PA manifest is bound to the exact bytes and does not survive any
re-encode. ``convert_image_to_webp()`` in ``Word.save()`` short-circuits on
WebP input, so nothing touches the pixels; editor uploads still convert as
before.

Because of this, the file extension has to travel with the bytes through the
whole path (temporary file, store-permanently view, ``ImageField``). Storing
OpenAI's WebP under a ``.png`` name would trigger a re-encode and strip the
markings. Anything that resizes or re-compresses a generated image has the
same effect.

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
   * - ``LUNES_CMS_OPENAI_IMAGE_OUTPUT_FORMAT``
     - ``webp``
     - Format OpenAI encodes the image in (``webp`` / ``png`` / ``jpeg``)
   * - ``LUNES_CMS_OPENAI_IMAGE_OUTPUT_COMPRESSION``
     - ``85``
     - Compression level (0-100) for ``webp`` / ``jpeg`` output
