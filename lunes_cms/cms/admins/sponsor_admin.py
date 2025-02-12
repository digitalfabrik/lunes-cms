from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ..utils import get_image_tag


class SponsorAdmin(admin.ModelAdmin):
    """
    Admin interface that is used to edit sponsor objects in the CMS.
    """

    fields = [
        "name",
        "url",
        "logo",
        "image_tag",
    ]
    readonly_fields = ["image_tag"]
    list_display = [
        "name",
        "has_logo",
    ]
    list_per_page = 25

    def has_logo(self, sponsor):
        """
        Additional field to display whether a logo is set for the sponsor in the list view.

        :param sponsor: Sponsor object
        :type sponsor: ~lunes_cms.cms.models.sponsor.Sponsor
        :return: Whether the sponsor has a logo
        :rtype: bool
        """

        return bool(sponsor.logo)

    has_logo.boolean = True
    has_logo.short_description = _("logo")

    def image_tag(self, sponsor):
        """
        Image thumbnail to display a preview of a image in the form view.

        :param sponsor: Sponsor object
        :type sponsor: ~lunes_cms.cms.models.sponsor.Sponsor
        :return: img HTML tag to display an image thumbnail
        :rtype: str
        """
        return get_image_tag(sponsor.logo)

    image_tag.short_description = ""

    class Media:
        """
        Media class of Sponsor Admin
        """

        js = ("js/image_preview.js",)
