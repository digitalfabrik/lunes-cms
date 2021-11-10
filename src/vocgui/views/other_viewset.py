import json
from django.shortcuts import render
from django.shortcuts import redirect
from vocgui.models import TrainingSet, Document, DocumentImage, Discipline


def redirect_view(request):
    """
    Redirect root URL

    :param request: Current HTTP request
    :param type: HttpRequest

    :return: Redirection to api/
    :rtype: HttpResponse
    """
    return redirect("api/")


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
                    name=document.word,
                    confirmed=False,
                )
                image.save()
                upload_success = True
    missing_images = Document.objects.values_list(
        "id", "word", "article", "training_sets"
    ).filter(document_image__isnull=True)
    training_sets = (
        TrainingSet.objects.values_list("id", "title", "discipline__id")
        .filter(documents__document_image__isnull=True)
        .distinct()
    )
    disciplines = (Discipline.objects.values_list("id", "title", "training_sets__id")
        .filter(training_sets__isnull=False)
        .filter(training_sets__documents__document_image__isnull=True).distinct()
    )
    context = {
        "documents": json.dumps(list(missing_images)),
        "disciplines": json.dumps(list(disciplines)),
        "training_sets": json.dumps(list(training_sets)),
        "upload_success": upload_success,
    }
    return render(request, "public_upload.html", context)
