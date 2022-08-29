from django.templatetags.static import static
from rest_framework import serializers


class FallbackIconSerializer(serializers.ModelSerializer):
    """
    Serializer for models with an icon field which should provide a fallback value
    """

    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        """
        Get the the icon if it exists and a fallback image otherwise

        :param obj: The model instance
        :type obj: ~django.db.models.Model

        :return: The url to the icon
        :rtype: str
        """
        if obj.icon:
            url = obj.icon.url
        else:
            url = static("images/fallback-icon.svg")
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url
