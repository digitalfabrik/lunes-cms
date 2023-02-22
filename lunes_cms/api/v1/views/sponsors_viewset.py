from rest_framework import viewsets

from ....cms.models import Sponsor
from ..serializers import SponsorSerializer


class SponsorsViewSet(viewsets.ModelViewSet):
    """
    View to provide a queryset of all current sponsors in the app.
    """

    serializer_class = SponsorSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        """
        Get the queryset of the current sponsors managed by the cms.

        :return: The queryset of disciplines
        :rtype: ~django.db.models.query.QuerySet
        """
        if getattr(self, "swagger_fake_view", False):
            return Sponsor.objects.none()
        return Sponsor.objects.all()
