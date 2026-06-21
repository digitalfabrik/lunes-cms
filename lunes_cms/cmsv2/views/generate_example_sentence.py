from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openai import OpenAIError

from lunes_cms.cmsv2.models import Job, Word
from lunes_cms.cmsv2.models.unit import UnitWordRelation
from lunes_cms.cmsv2.services.sentence_generation import openai_example_sentence
from lunes_cms.cmsv2.utils import OpenAIConfigurationError


def _generate_sentence_response(word, job_names, unit_title=None):
    """
    Run the OpenAI generation and wrap the result/errors in a JsonResponse.
    """
    if not job_names:
        return JsonResponse(
            {
                "error": "No job found. Assign the word to a unit that belongs to a job first."
            },
            status=400,
        )

    try:
        sentence = openai_example_sentence(word, ", ".join(job_names), unit_title)
    except OpenAIConfigurationError as e:
        return JsonResponse({"error": str(e)}, status=503)
    except (OpenAIError, ValueError, ConnectionError, TimeoutError) as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse(
        {
            "message": "Example sentence generated!",
            "example_sentence": sentence,
        }
    )


@staff_member_required
@csrf_exempt
@require_POST
def word_generate_example_sentence_via_openai(_request, word_id):
    """
    AJAX endpoint to generate an example sentence for a Word via OpenAI.

    The professional context is derived from the jobs of all units the word
    is assigned to.
    """
    word_instance = get_object_or_404(Word, pk=word_id)
    # A word can belong to several jobs (via the units it is assigned to);
    # all of them are joined into the prompt so the generated sentence covers
    # every relevant professional context.
    job_names = list(
        Job.objects.filter(units__words=word_instance)
        .distinct()
        .order_by("name")
        .values_list("name", flat=True)
    )
    return _generate_sentence_response(word_instance.word, job_names)


@staff_member_required
@csrf_exempt
@require_POST
def unitword_generate_example_sentence_via_openai(_request, unitword_id):
    """
    AJAX endpoint to generate an example sentence for a UnitWordRelation via
    OpenAI, scoped to the relation's unit and its jobs.
    """
    relation = get_object_or_404(UnitWordRelation, pk=unitword_id)
    job_names = list(relation.unit.jobs.order_by("name").values_list("name", flat=True))
    return _generate_sentence_response(
        relation.word.word, job_names, relation.unit.title
    )


def _store_sentence_response(instance, sentence):
    """
    Persist a kept example sentence on the given instance and wrap the result in
    a JsonResponse. Saving resets the example sentence check status and clears
    any stale audio, mirroring a regular form save.
    """
    if sentence is None:
        return JsonResponse(
            {"status": "error", "message": "No example sentence provided."},
            status=400,
        )
    instance.example_sentence = sentence
    instance.save()
    return JsonResponse(
        {
            "status": "success",
            "message": "Example sentence saved.",
            "example_sentence": instance.example_sentence,
        }
    )


@staff_member_required
@csrf_exempt
@require_POST
def word_store_generated_example_sentence(request, word_id):
    """
    AJAX endpoint to persist a kept example sentence on a Word.
    """
    word_instance = get_object_or_404(Word, pk=word_id)
    return _store_sentence_response(word_instance, request.POST.get("example_sentence"))


@staff_member_required
@csrf_exempt
@require_POST
def unitword_store_generated_example_sentence(request, unitword_id):
    """
    AJAX endpoint to persist a kept example sentence on a UnitWordRelation.
    """
    relation = get_object_or_404(UnitWordRelation, pk=unitword_id)
    return _store_sentence_response(relation, request.POST.get("example_sentence"))
