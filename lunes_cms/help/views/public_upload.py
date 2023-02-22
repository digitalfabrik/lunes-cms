import json

from django.shortcuts import render

from ...cms.models import TrainingSet, Document, DocumentImage, Discipline


def public_upload(request):
    """Public form to upload missing images

    :param request: current user request
    :type request: django.http.request
    :return: rendered response
    :rtype: HttpResponse
    """
    upload_success = False
    if request.method == "POST":
        document = Document.objects.get(id=request.POST.get("inputDocument", None))
        if document:
            uploaded_image = request.FILES.get("inputFile", None)
            if uploaded_image:
                image = DocumentImage(
                    document=document,
                    image=uploaded_image,
                    confirmed=False,
                )
                image.save()
                upload_success = True
    missing_images = Document.objects.values_list(
        "id", "word", "article", "training_sets"
    ).filter(document_image__isnull=True)
    training_sets = (
        TrainingSet.objects.values_list("id", "title")
        .filter(documents__document_image__isnull=True)
        .distinct()
    )
    disciplines = (
        Discipline.objects.values_list("id", "title")
        .order_by("title")
        .filter(training_sets__isnull=False)
        .filter(training_sets__documents__document_image__isnull=True)
        .distinct()
    )
    disc_sets_map = (
        Discipline.objects.values_list("id", "training_sets__id")
        .filter(training_sets__isnull=False)
        .filter(training_sets__documents__document_image__isnull=True)
        .distinct()
    )

    new_map = {}
    for key, value in disc_sets_map:
        if key in new_map:
            new_map[key].append(value)
        else:
            new_map[key] = [value]

    context = {
        "documents": json.dumps(list(missing_images)),
        "disciplines": json.dumps(list(disciplines)),
        "disc_sets_map": json.dumps(new_map),
        "training_sets": json.dumps(list(training_sets)),
        "upload_success": upload_success,
    }
    return render(request, "public_upload.html", context)
