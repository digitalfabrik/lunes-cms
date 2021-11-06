from django.db import models
from rest_framework_api_key.models import AbstractAPIKey
from django.contrib.auth.models import Group
from django.utils.translation import ugettext_lazy as _


class GroupAPIKey(AbstractAPIKey):
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
