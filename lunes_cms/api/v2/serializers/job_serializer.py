from rest_framework import serializers

from ....cmsv2.models import Job


class JobSerializer(serializers.ModelSerializer):
    """
    Serializer for Jobs.
    """

    number_units = serializers.IntegerField()

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Job
        fields = ("id", "name", "icon", "number_units")
