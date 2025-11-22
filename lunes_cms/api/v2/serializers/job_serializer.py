from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ....cmsv2.models import Job


class JobSerializer(serializers.ModelSerializer):
    """
    Serializer for Jobs.
    """

    number_units = serializers.IntegerField()
    migrated = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_migrated(self, obj):
        """Return True if the job was migrated from the old data model"""
        return obj.v1_id is not None

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Job
        fields = ("id", "name", "icon", "number_units", "migrated")
