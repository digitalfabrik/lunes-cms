from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Job


@staff_member_required
@csrf_exempt
@require_POST
def update_job_icon(request, job_id):
    """
    Update the icon for a job.

    Args:
        request: The HTTP request
        job_id: The ID of the job to update

    Returns:
        JsonResponse: A response indicating success or failure
    """
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Job not found"}, status=404)

    action = request.POST.get("action")

    if action in ("add", "replace"):
        if "icon" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": "No icon provided"}, status=400
            )

        job.icon = request.FILES["icon"]
        job.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Icon added successfully",
                "icon_url": job.icon.url if job.icon else None,
            }
        )

    if action == "delete":
        if job.icon:
            job.icon.delete()
            job.icon = None
            job.save()

            return JsonResponse(
                {"status": "success", "message": "Icon deleted successfully"}
            )

        return JsonResponse(
            {"status": "error", "message": "No icon to delete"}, status=400
        )

    return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)
