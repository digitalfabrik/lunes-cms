"""
REST-Framework
"""
from django.http import HttpResponse
from django.core import serializers
from django.shortcuts import render
from rest_framework import viewsets
from django.shortcuts import redirect
from django.db.models import Count, Q

from .models import TrainingSet, Document, AlternativeWord, Discipline
from .serializers import (
    DisciplineSerializer,
    DocumentSerializer,
    TrainingSetSerializer,
    AlternativeWordSerializer,
    DocumentImageSerializer,
)


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
        if 'group_id' in self.kwargs:
            groups = self.kwargs["group_id"].split("&")
            queryset = (
                Discipline.objects.filter(
                    Q(released=True) & (Q(creator_is_admin=True) | Q(created_by__in=groups))
                )
                .order_by("order")
                .annotate(
                    total_training_sets=Count(
                        "training_sets", filter=Q(training_sets__released=True)
                    )
                )
            )
        else:
            queryset = (
                Discipline.objects.filter(
                    Q(released=True) & Q(creator_is_admin=True)
                )
                .order_by("order")
                .annotate(
                    total_training_sets=Count(
                        "training_sets", filter=Q(training_sets__released=True)
                    )
                )
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
        queryset = Document.objects.filter(
            training_sets__id=self.kwargs["training_set_id"]
        ).select_related()
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
            .annotate(total_documents=Count("documents"))
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
