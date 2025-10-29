from rest_framework import serializers

from ....cms.models import Sponsor


class SponsorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Sponsor module.
    """

    class Meta:
        """
        Define model and the corresponding fields for the display in the cms.
        """

        model = Sponsor
        fields = (
            "id",
            "name",
            "url",
            "logo",
        )
