from django.contrib.auth.models import Group
from rest_framework import serializers

from ....cms.models import Discipline


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for the Group module. Inherits from
    `serializers.ModelSerializer`.
    """

    total_discipline_children = serializers.SerializerMethodField(
        "get_total_discipline_children"
    )

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Group
        fields = (
            "id",
            "name",
            "icon",
            "total_discipline_children",
        )

    def get_total_discipline_children(self, obj):
        """Returns the total child count of a group.
        A child itself or one of its sub-children needs to
        contain at least one training set.

        :param disc: Discipline instance
        :type disc: models.Discipline
        :return: sum of children
        :rtype: int
        """
        queryset = Discipline.objects.filter(released=True, created_by=obj.id)
        queryset = [obj for obj in queryset if obj.is_root_node() and obj.is_valid()]
        return len(queryset)
