from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Job, Word, Unit
from .models.unit import UnitWordRelation


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


@staff_member_required
@csrf_exempt
@require_POST
def update_word_audio(request, word_id):
    """
    Update the audio file for a word.

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
        if "audio" not in request.FILES:
            return JsonResponse(
                {"status": "error", "message": "No audio file provided"}, status=400
            )

        word.audio = request.FILES["audio"]
        word.save()

        return JsonResponse(
            {
                "status": "success",
                "message": "Audio added successfully",
                "audio_url": word.audio.url if word.audio else None,
            }
        )

    if action == "delete":
        if word.audio:
            word.audio.delete()
            word.audio = None
            word.save()

            return JsonResponse(
                {"status": "success", "message": "Audio deleted successfully"}
            )

        return JsonResponse(
            {"status": "error", "message": "No audio file to delete"}, status=400
        )

    return JsonResponse({"status": "error", "message": "Invalid action"}, status=400)


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


@staff_member_required
@csrf_exempt
@require_POST
def update_word_image_check_status(request, word_id):
    """
    Update the image check status for a word.

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

    image_check_status = request.POST.get("image_check_status")
    if not image_check_status:
        return JsonResponse(
            {"status": "error", "message": "No image check status provided"}, status=400
        )

    word.image_check_status = image_check_status
    word.save()

    return JsonResponse(
        {"status": "success", "message": "Image check status updated successfully"}
    )


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
