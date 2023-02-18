from django.db import models
from django.utils.translation import ugettext_lazy as _

from .static import upload_sponsor_icons


class Sponsor(models.Model):
    """
    Model to manage our sponsors that are shown in the app.
    """

    name = models.TextField(verbose_name=_("name"),)

    icon = models.ImageField(
        upload_to=upload_sponsor_icons, blank=True, verbose_name=_("icon")
    )
