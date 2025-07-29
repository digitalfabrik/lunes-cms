from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models.unit import UnitWordRelation


@staff_member_required
@csrf_exempt
@require_POST
def update_unitword_image(request, unitword_id):
    """
    Update the image for a unit-word relation.

    Args:
        request: The HTTP request
        unitword_id: The ID of the unit-word relation to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        unitword = UnitWordRelation.objects.get(id=unitword_id)
    except UnitWordRelation.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Unit-Word relation not found"}, status=404
        )

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "image" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": "No image provided"}, status=400
            )

        unitword.image = request.FILES["image"]
        unitword.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Image added successfully",
                "image_url": unitword.image.url if unitword.image else None,
            }
        )

    if action == "delete":
        if unitword.image:
            unitword.image.delete()
            unitword.image = None
            unitword.save()

            return JsonResponse(
                {"status": "success", "message": "Image deleted successfully"}
            )

        return JsonResponse(
            {"status": "error", "message": "No image to delete"}, status=400
        )

    return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)
