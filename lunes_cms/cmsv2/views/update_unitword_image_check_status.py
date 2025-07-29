from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models.unit import UnitWordRelation


@staff_member_required
@csrf_exempt
@require_POST
def update_unitword_image_check_status(request, unitword_id):
    """
    Update the image check status for a unit-word relation.

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

    image_check_status = request.POST.get("image_check_status")
    if not image_check_status:
        return JsonResponse(
            {"status": "error", "message": "No image check status provided"}, status=400
        )

    unitword.image_check_status = image_check_status
    unitword.save()

    return JsonResponse(
        {
            "status": "success",
            "message": "Unit-Word image check status updated successfully",
        }
    )
