from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from ..areas import visible_unit_word_relations
from ..models.unit import UnitWordRelation
from .decorators import require_any_permission_json


@login_required
@require_any_permission_json("cmsv2.change_unitwordrelation")
@require_POST
def update_unitword_image(request: HttpRequest, unitword_id: int) -> JsonResponse:
    """
    Update the image for a unit-word relation.

    Args:
        request: The HTTP request
        unitword_id: The ID of the unit-word relation to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        unitword = visible_unit_word_relations(request.user).get(id=unitword_id)
    except UnitWordRelation.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": _("Unit-Word relation not found")},
            status=404,
        )

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "image" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": _("No image provided")}, status=400
            )

        unitword.image = request.FILES["image"]
        unitword.save()

        return JsonResponse(
            {
                "status": "success",
                "message": _("Image added successfully"),
                "image_url": unitword.image.url if unitword.image else None,
            }
        )

    if action == "delete":
        if unitword.image:
            unitword.image.delete()
            unitword.image = None
            unitword.save()

            return JsonResponse(
                {"status": "success", "message": _("Image deleted successfully")}
            )

        return JsonResponse(
            {"status": "error", "message": _("No image to delete")}, status=400
        )

    return JsonResponse({"status": "error", "message": _("Invalid action")}, status=400)
