from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Word


@staff_member_required
@csrf_exempt
@require_POST
def update_word_image(request, word_id):
    """
    Update the image for a word.

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

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "image" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": "No image provided"}, status=400
            )

        word.image = request.FILES["image"]
        word.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Image added successfully",
                "image_url": word.image.url if word.image else None,
            }
        )

    if action == "delete":
        if word.image:
            word.image.delete()
            word.image = None
            word.save()

            return JsonResponse(
                {"status": "success", "message": "Image deleted successfully"}
            )

        return JsonResponse(
            {"status": "error", "message": "No image to delete"}, status=400
        )

    return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)
