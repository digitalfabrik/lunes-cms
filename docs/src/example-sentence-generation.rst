****************************
Example Sentence Generation
****************************

Lunes can generate example sentences for vocabulary via the OpenAI chat API.
The vocabulary admin can trigger it per word and per unit<>word relation; the
generated sentence is pasted into the example sentence textbox so it can be
reviewed, adjusted and saved by the editor.

This requires an API key; without it the feature is simply disabled (a warning
is logged on startup) and everything else keeps working.

How it works
============

A *Generate example sentence* button is shown below the example sentence
textbox in two places:

* On the word edit page. The professional context for the prompt is derived
  from the jobs of all units the word is assigned to. If the word is not
  assigned to any unit with a job, an error is shown instead.
* On unit<>word relation rows (inlines on the word and unit edit pages). Here
  the prompt additionally includes the title of the unit, so the sentence fits
  the learning unit. The relation has to be saved once before the button
  appears.

Clicking the button calls OpenAI in the background and shows a loading
animation; on success the sentence is filled into the textbox above, on error
the reason is displayed next to the button. Nothing is stored automatically —
the editor always saves the (possibly adjusted) sentence manually.

The prompt asks for a short German sentence (5-10 words) from the everyday
working life of the given job, mainly at language level B1 (occasionally B2),
with varying sentence types and term positions.

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
     - OpenAI API key (required to enable example sentence generation)
   * - ``LUNES_CMS_OPENAI_TEXT_MODEL``
     - ``gpt-4.1``
     - Model used for text generation
