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

    def get_total_discipline_children(self, group):
        """Returns the total child count of a group.
        A child itself or one of its sub-children needs to
        contain at least one training set.

        :param group: Group instance
        :type group: django.contrib.auth.models.Group
        :return: sum of children
        :rtype: int
        """
        queryset = Discipline.objects.filter(released=True, created_by=group.id)
        queryset = [
            discipline
            for discipline in queryset
            if discipline.is_root_node() and discipline.is_valid()
        ]
        return len(queryset)
