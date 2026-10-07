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
image is requested from OpenAI's image *edit* endpoint with the European
Commission's "AI GENERATED" icon (``cmsv2/assets/ai_generated_label.png``) as
the reference image. Every prompt ends with the instruction to place that icon
unchanged in the bottom-right corner, about a fifth of the image width wide. The
default ban on text inside the image (issue #918) exempts the label explicitly.

The model still redraws the icon, so it is close to the original but not
pixel-exact, and an editor checks it like any other part of the image.
``input_fidelity`` is not passed, because ``gpt-image-2`` does not accept it.

Generated images are requested from OpenAI **in the format we serve**
(``webp``) rather than converted afterwards. The stored file is then
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
label* (stored before the label existed), *AI-generated, labeled
afterwards* (``AI_MARKED``), or *unknown*. The code paths that store a
generated image pass the source to ``save()``; every other new image counts as
an upload, and removing the image resets the source to *unknown*. The "Image
source" filter in the word admin matches a word by its own image or by any of
its unit images.

Images stored before the field existed start as *unknown*. Their source is
judged from the file: a C2PA manifest means a labeled generated image (see
above), a plain 1024x1024 image means a generated image from before the label,
anything else an upload.

Marking unlabeled images
------------------------

``mark_unlabeled_images`` records the source of every *unknown* image, then
marks the *AI-generated without label* images stored on or after ``--since``
(default 2025-06-23, the day image generation was added) without generating
them again. The storage time comes from the version 1 UUID in the file name,
which the WebP conversion keeps. Uploads are never touched.

.. code-block:: bash

   lunes-cms-cli mark_unlabeled_images --dry-run
   lunes-cms-cli mark_unlabeled_images [--since YYYY-MM-DD] [--limit N]

Marking an image means adding the label and the marking to it:

* the "AI GENERATED" label (the Commission's official icon,
  ``cmsv2/assets/ai_generated_label.png``) is pasted into the bottom-right
  corner, 20 % of the image width wide, and
* an XMP packet is embedded with the IPTC ``DigitalSourceType``
  ``trainedAlgorithmicMedia``, the value OpenAI's own C2PA manifest asserts.

The file is re-encoded as WebP (quality 95) and stored under a new name, the old
name with ``-marked`` added before the extension: apps cache images by URL, so
a new URL makes them fetch the marked image. The old file is deleted once no
word or unit-word relation uses it, and the permissions of the old file carry
over. OpenAI's C2PA manifest is not restored, so the XMP packet is the only
machine-readable marking of these images. The check status stays as it is, and
the image is marked *labeled afterwards*, so the "Image source" filter in the
word admin lists the marked images.

An image that fails is logged and left as it was, and the run continues. Running
the command again picks up only the images that are still unlabeled, and an
image that already carries the XMP packet is never marked a second time, but it
is still recorded as *labeled afterwards*.

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
