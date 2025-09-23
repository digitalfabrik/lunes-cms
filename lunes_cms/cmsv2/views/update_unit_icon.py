from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Unit


@staff_member_required
@csrf_exempt
@require_POST
def update_unit_icon(request, unit_id):
    """
    Update the icon for a unit.

    Args:
        request: The HTTP request
        unit_id: The ID of the unit to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        unit = Unit.objects.get(id=unit_id)
    except Unit.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Unit not found"}, status=404
        )

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "icon" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": "No icon provided"}, status=400
            )

        unit.icon = request.FILES["icon"]
        unit.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Icon added successfully",
                "icon_url": unit.icon.url if unit.icon else None,
            }
        )

    if action == "delete":
        if unit.icon:
            unit.icon.delete()
            unit.icon = None
            unit.save()

            return JsonResponse(
                {"status": "success", "message": "Icon deleted successfully"}
            )

        return JsonResponse(
            {"status": "error", "message": "No icon to delete"}, status=400
        )

    return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)
