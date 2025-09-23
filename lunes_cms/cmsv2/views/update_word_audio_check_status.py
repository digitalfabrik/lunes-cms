from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Word


@staff_member_required
@csrf_exempt
@require_POST
def update_word_audio_check_status(request, word_id):
    """
    Update the audio check status for a word.

    Args:
        request: The HTTP request
        word_id: The ID of the word to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        word = Word.objects.get(id=word_id)
    except Word.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Word not found"}, status=404
        )

    audio_check_status = request.POST.get("audio_check_status")
    if not audio_check_status:
        return JsonResponse(
            {"status": "error", "message": "No audio check status provided"}, status=400
        )

    word.audio_check_status = audio_check_status
    word.save()

    return JsonResponse(
        {"status": "success", "message": "Audio check status updated successfully"}
    )
