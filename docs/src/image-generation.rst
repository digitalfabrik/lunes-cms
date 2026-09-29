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

Image source
============

``Word`` and ``UnitWordRelation`` record where their image came from in
``image_source``: *uploaded*, *AI-generated with label*, *AI-generated without
label* (stored before the label existed), *regenerated with AI label*, or
*unknown*. The code paths that store a generated image pass the source to
``save()``; every other new image counts as an upload, and removing the image
resets the source to *unknown*. The "Image source" filter in the word admin
matches a word by its own image or by any of its unit images.

Images stored before the field existed start as *unknown*. Their source is
judged from the file: a C2PA manifest means a labeled generated image (see
above), a plain 1024x1024 image means a generated image from before the label,
anything else an upload.

Regenerating unlabeled images
-----------------------------

``regenerate_unlabeled_images`` records the source of every *unknown* image,
then regenerates the *AI-generated without label* images stored on or after
``--since`` (default 2026-08-02). The storage time comes from the version 1
UUID in the file name, which the WebP conversion keeps. Uploads are never
touched.

.. code-block:: bash

   lunes-cms-cli regenerate_unlabeled_images --dry-run
   lunes-cms-cli regenerate_unlabeled_images [--since YYYY-MM-DD] [--limit N] [--delay SECONDS]

The prompt is the default one for the word (plus unit and job, like in the
admin): editor hints and the "allow text" setting of the original generation
were never stored. A regenerated image keeps its check status, so it is marked
*regenerated with AI label* instead — filter the words by that source to review
them. The replaced file is deleted.

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
   * - ``LUNES_CMS_OPENAI_IMAGE_OUTPUT_COMPRESSION``
     - ``85``
     - Compression level (0-100) OpenAI applies to the generated WebP
