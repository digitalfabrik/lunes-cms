from rest_framework import serializers


class DocumentImageListSerializer(serializers.ListSerializer):
    """
    List Serializer for the DocumentImage module. Inherits from
    `serializers.ListSerializer`.
    """

    def update(self, instance, validated_data):
        raise NotImplementedError(
            "Serializers with many=True do not support multiple update by "
            "default, only multiple create. For updates it is unclear how to "
            "deal with insertions and deletions. If you need to support "
            "multiple update, use a `ListSerializer` class and override "
            "`.update()` so you can specify the behavior exactly."
        )

    def to_representation(self, data):
        """
        Overwrite django built-in function to only deliver
        approved images.

        :param data: model instance
        :type data: models.Model
        :return: serialized model data
        :rtype: dict
        """
        data = data.filter(confirmed=True)
        return super().to_representation(data)
