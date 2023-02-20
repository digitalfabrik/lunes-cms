from django.db import models
from django.utils.translation import ugettext_lazy as _

from .static import upload_sponsor_icons
from ..utils import get_image_tag
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

    icon = models.ImageField(
        upload_to=upload_sponsor_icons,
        validators=[validate_multiple_extensions],
        blank=True,
        verbose_name=_("icon"),
    )

    def __str__(self):
        """
        String representation of sponsor name

        :return: name of the sponsor
        :rtype: str
        """
        return self.name

    def preview(self):
        """
        Image thumbnail to display a preview of a image in the editing section
        of the DocumentSponsor admin.

        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        return get_image_tag(self.icon, width=100)

    def icon_is_set(self):
        """
        Additional field to display whether a icon is set for the sponsor in the list view.

        :return: Returns True if an icon is set or False if no icon is set.
        :rtype: bool
        """

        return bool(self.icon)

    icon_is_set.boolean = True
    icon_is_set.short_description = _("icon")
