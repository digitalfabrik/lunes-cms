from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework_api_key.crypto import KeyGenerator
from rest_framework_api_key.models import AbstractAPIKey, BaseAPIKeyManager

from ..utils import get_random_key


class CustomKeyGenerator(KeyGenerator):
    """
    Custom KeyGenerator that creates custom api keys, e.g. with a specific length or excluded characters.
    """

    def __init__(
        self,
        prefix_length: int,
        secret_key_length: int,
        excluded_chars: list = [],
    ):
        """Initialize KeyGenerator

        :param prefix_length: length of prefix, defaults to 3
        :type prefix_length: int, optional
        :param secret_key_length: length of secret, defaults to 7
        :type secret_key_length: int, optional
        :param excluded_chars: list of characters that should be excluded (mixed dtypes are possible), defaults to []
        :type excluded_chars: list, optional
        """
        super().__init__(
            prefix_length=prefix_length, secret_key_length=secret_key_length
        )
        self.excluded_chars = excluded_chars

    def get_prefix(self) -> str:
        """Generate prefix

        :return: Key prefix
        :rtype: str
        """
        return get_random_key(self.prefix_length, self.excluded_chars)

    def get_secret_key(self) -> str:
        """Generate secret

        :return: Key secret
        :rtype: str
        """
        return get_random_key(self.secret_key_length, self.excluded_chars)


class GroupAPIKeyManager(BaseAPIKeyManager):
    """
    Custom APIKeyManager that creates custom api keys, e.g. with a specific length or excluded characters.
    """

    key_generator = CustomKeyGenerator(
        prefix_length=3, secret_key_length=7, excluded_chars=[1, 0, "I", "l", "o", "O"]
    )


class GroupAPIKey(AbstractAPIKey):
    """
    Model that handles api keys associated with a user group.
    """

    objects = GroupAPIKeyManager()
    organization = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )

    def __str__(self):
        return self.name + ": Token für die Organisation " + str(self.organization)

    class Meta:
        """
        Define user readable name of Document
        """

        verbose_name = _("API Key")
        verbose_name_plural = _("API Keys")
