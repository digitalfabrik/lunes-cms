from rest_framework import mixins, viewsets

from ..serializers import FeedbackSerializer


class CreateFeedbackViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    A viewset that provides only the ``create`` action for feedback elements.
    """

    serializer_class = FeedbackSerializer
