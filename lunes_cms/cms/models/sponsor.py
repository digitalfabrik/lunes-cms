from django.db import models
from django.utils.translation import ugettext_lazy as _

from .static import upload_sponsor_logos
from ..validators import validate_multiple_extensions


class Sponsor(models.Model):
    """
    Model to manage our sponsors that are shown in the app.
    """

    name = models.CharField(
        verbose_name=_("name"),
        max_length=255,
        blank=False,
    )
    url = models.URLField(
        blank=True,
        verbose_name=_("URL"),
    )
    logo = models.ImageField(
        upload_to=upload_sponsor_logos,
        validators=[validate_multiple_extensions],
        blank=True,
        verbose_name=_("logo"),
    )

    def __str__(self):
        """
        String representation of sponsor name

        :return: name of the sponsor
        :rtype: str
        """
        return self.name

    class Meta:
        """
        Define user readable name of sponsors
        """

        verbose_name = _("sponsor")
        verbose_name_plural = _("sponsors")
