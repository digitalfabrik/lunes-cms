from rest_framework import serializers

from ....cmsv2.models import Unit


class UnitSerializer(serializers.ModelSerializer):
    """
    Serializer for units.
    """

    number_words = serializers.IntegerField()

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Unit
        fields = (
            "id",
            "title",
            "description",
            "icon",
            "number_words",
        )
