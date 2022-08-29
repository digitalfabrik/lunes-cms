from rest_framework import serializers


class DocumentImageListSerializer(serializers.ListSerializer):
    """
    List Serializer for the DocumentImage module. Inherits from
    `serializers.ListSerializer`.
    """

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
        return super(DocumentImageListSerializer, self).to_representation(data)
