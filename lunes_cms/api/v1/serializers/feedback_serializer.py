from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ....cms.models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer for the Feedback module. Inherits from
    'serializers.ModelSerializer'.
    """

    content_type = serializers.SlugRelatedField(
        slug_field="model",
        queryset=ContentType.objects.filter(
            app_label="cms", model__in=["discipline", "trainingset", "document"]
        ),
        error_messages={
            "does_not_exist": _(
                "The content type must be either 'discipline', 'training set' or"
                " 'document'."
            ),
        },
    )

    def validate(self, attrs):
        try:
            attrs["content_type"].model_class().objects.get(pk=attrs["object_id"])
        except ObjectDoesNotExist as e:
            print(e)
            raise serializers.ValidationError(
                {
                    "object_id": [
                        _("{} with id {} does not exist.").format(
                            attrs["content_type"].name, attrs["object_id"]
                        ),
                    ]
                }
            ) from e
        return attrs

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Feedback
        fields = (
            "comment",
            "content_type",
            "object_id",
        )
