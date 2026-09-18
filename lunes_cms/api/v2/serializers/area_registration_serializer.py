from __future__ import annotations

from rest_framework import serializers

from ....cmsv2.models import Area


class AreaSerializer(serializers.ModelSerializer):
    """
    Serializer for the area a client was granted access to.
    """

    class Meta:
        """
        Define model and the corresponding fields
        """

        model = Area
        fields = (
            "id",
            "name",
            "logo",
            "primary_color",
            "secondary_color",
            "additional_information",
            "additional_information_url",
        )


# pylint: disable=abstract-method
class AreaCodeSerializer(serializers.Serializer):
    """
    Serializer base for a request that carries the code of an area.

    Shared by everything that looks a code up, whether or not it goes on to
    register a client with it.
    """

    code = serializers.CharField(max_length=50, write_only=True)

    def validate_code(self, value: str) -> str:
        """
        Normalize the code before it is looked up.

        A code is read off a printout, a QR code or a deep link and may be
        typed by hand, so surrounding whitespace is dropped and lower case
        letters are turned into upper case ones. Codes themselves only ever
        consist of digits and upper case letters.

        :param value: The code the client sent
        :return: The normalized code
        """
        return value.strip().upper()


# pylint: disable=abstract-method
class AreaRegistrationSerializer(AreaCodeSerializer):
    """
    Serializer for redeeming the code of an area.

    Redeeming a code creates an access token, not the code itself, so this
    serializer validates the request and leaves the writing to the view.
    """

    installation_id = serializers.CharField(
        max_length=255, required=False, allow_blank=True, write_only=True
    )


# pylint: disable=abstract-method
class AreaRegistrationResponseSerializer(serializers.Serializer):
    """
    Serializer for the answer to a successful registration.

    The token is only ever sent here, because the server stores nothing but its
    hash. A client that lost it has to redeem its code again.
    """

    token = serializers.CharField(read_only=True)
    area = AreaSerializer(read_only=True)


# pylint: disable=abstract-method
class AreaInfoResponseSerializer(serializers.Serializer):
    """
    Serializer for the answer to an area info lookup.

    No token is issued and no client is registered here: this only tells a
    caller which area a code belongs to, e.g. to show its branding before the
    code is actually redeemed.
    """

    area = AreaSerializer(read_only=True)
