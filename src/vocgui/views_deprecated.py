"""
REST-Framework
"""
import json

from django.shortcuts import render
from rest_framework import viewsets
from django.shortcuts import redirect
from django.db.models import Count, Q
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models.functions import Floor
from django.db.models import F

from vocgui.models import training_set

from .models import TrainingSet, Document, AlternativeWord, Discipline, DocumentImage
from .serializers import (
    DisciplineSerializer,
    DocumentSerializer,
    TrainingSetSerializer,
    AlternativeWordSerializer,
    DocumentImageSerializer,
)
from .utils import get_child_count


class DisciplineViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Discipline module, optionally filtered by user groups.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DisciplineViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Discipline.objects.none()
        if "group_id" in self.kwargs:
            groups = self.kwargs["group_id"].split("&")
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if obj.get_descendant_count() == 0
                    ]
                )
                & (Q(creator_is_admin=True) | Q(created_by__in=groups))
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
                total_discipline_children=Count("children"),
            )
        else:
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(creator_is_admin=True)
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if obj.get_descendant_count() == 0
                    ]
                )
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
                total_discipline_children=Count("children"),
            )
        return queryset


class DisciplineLevelViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Discipline module, optionally filtered respected to
    the different mptt levels. If no discipline id is given, all root elements will
    be displayed.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    queryset = Discipline.objects.all()
    serializer_class = DisciplineSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DisciplineViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Discipline.objects.none()
        if "discipline_id" in self.kwargs:
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(creator_is_admin=True)
                & Q(
                    id__in=Discipline.objects.get(
                        id=self.kwargs["discipline_id"]
                    ).get_children()
                )
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if get_child_count(obj)
                        + obj.training_sets.filter(released=True).count()
                        > 0
                    ]
                )
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
            )
        else:
            queryset = Discipline.objects.filter(
                Q(released=True)
                & Q(creator_is_admin=True)
                & Q(
                    id__in=[
                        obj.id
                        for obj in Discipline.objects.all()
                        if obj.is_root_node()
                        and get_child_count(obj)
                        + obj.training_sets.filter(released=True).count()
                        > 0
                    ]
                )
            ).annotate(
                total_training_sets=Count(
                    "training_sets", filter=Q(training_sets__released=True)
                ),
            )
        return queryset


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Document module.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    serializer_class = DocumentSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DocumentViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        user = self.request.user
        queryset = (
            Document.objects.filter(
                training_sets__id=self.kwargs["training_set_id"],
                document_image__confirmed=True,
            )
            .select_related()
            .distinct()
            .order_by("word")
        )
        return queryset


class DocumentByIdViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the Document module of a given id.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    serializer_class = DocumentSerializer
    http_method_names = ["get"]
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`DocumentViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        user = self.request.user
        queryset = Document.objects.filter(id=self.kwargs["document_id"])
        return queryset


class TrainingSetViewSet(viewsets.ModelViewSet):
    """
    Defines a view set for the TrainingSet module.
    Inherits from `viewsets.ModelViewSet` and defines queryset
    and serializers.
    """

    serializer_class = TrainingSetSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Defining custom queryset

        :param self: A handle to the :class:`TrainingSetViewSet`
        :type self: class

        :return: (filtered) queryset
        :rtype: QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return TrainingSet.objects.none()
        user = self.request.user
        queryset = (
            TrainingSet.objects.filter(
                discipline__id=self.kwargs["discipline_id"], released=True
            )
            .order_by("order")
            .annotate(
                total_documents=Count(
                    "documents",
                    filter=Q(documents__document_image__confirmed=True),
                    distinct=True,
                )
            )
        )
        return queryset


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
        TrainingSet.objects.values_list("id", "title")
        .filter(documents__document_image__isnull=True)
        .distinct()
    )
    context = {
        "documents": json.dumps(list(missing_images)),
        "training_sets": json.dumps(list(training_sets)),
        "upload_success": upload_success,
    }
    return render(request, "public_upload.html", context)
