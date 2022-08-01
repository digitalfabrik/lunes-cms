from rest_framework import serializers

from ....cms.models import Discipline
from ....cms.utils import get_child_count
from .fallback_icon_serializer import FallbackIconSerializer


class DisciplineSerializer(FallbackIconSerializer):
    """
    Serializer for the Discipline module. Inherits from
    `FallbackIconSerializer`.
    """

    total_training_sets = serializers.IntegerField()
    total_discipline_children = serializers.SerializerMethodField(
        "get_total_discipline_children"
    )
    nested_training_sets = serializers.ListSerializer(
        child=serializers.IntegerField(), source="get_nested_training_sets"
    )

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Discipline
        fields = (
            "id",
            "title",
            "description",
            "icon",
            "created_by",
            "total_training_sets",
            "total_discipline_children",
            "nested_training_sets",
        )

    def get_total_discipline_children(self, obj):
        """Returns the total child count by calling
        utils.get_child_count(obj).


        :param disc: Discipline instance
        :type disc: models.Discipline
        :return: sum of children
        :rtype: int
        """
        return get_child_count(obj)
